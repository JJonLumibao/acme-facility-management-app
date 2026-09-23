"""Reset the database and load demo data that exercises every feature. LOCAL DEVELOPMENT ONLY.

WARNING: deletes ALL existing users, facilities, incidents, notes and history.

Run from backend/api (same env vars as dev_server.py):
    IS_LOCAL=true POSTGRES_USER=postgres POSTGRES_PASS=postgres123 POSTGRES_NAME=postgres \
        .venv/bin/python seed.py --yes

Every demo account uses the password below. Incident histories are replayed through the same workflow
rules as the API (utils/workflow.py), with timestamps spread over the past month relative to "now",
so response times, timelines, hotspots and workload look realistic whenever the seed is re-run.

In the cloud it also runs automatically, once, on an empty database (seed_if_empty() in main.py), and facility
admins can restore the demo data any time from the app's account menu (POST /admin/reset-demo-data).
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from auth.security import hash_password
from db import get_connection, init_schema, transaction
from utils import workflow

# Local default. In the cloud Terraform injects a separate, generated DEMO_PASSWORD so the live site's
# password isn't in the code (read it with: terraform -chdir=infra output -raw demo_password).
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD") or "password123"

# Arbitrary constant for pg_advisory_xact_lock, so concurrent cold starts can't seed at the same time.
_SEED_LOCK_ID = 7_302_451

# key -> (email, full name, role, engineer profile or None)
USERS: Dict[str, tuple] = {
    "admin": ("admin@acme.inc", "Alex Morgan", "facility_admin", None),
    "jordan": ("jordan.lee@acme.inc", "Jordan Lee", "employee", None),
    "priya": ("priya.patel@acme.inc", "Priya Patel", "employee", None),
    "sam": ("sam.rivera@acme.inc", "Sam Rivera", "employee", None),
    "taylor": ("taylor.kim@acme.inc", "Taylor Kim", "employee", None),
    "chris": ("chris.walker@acme.inc", "Chris Walker", "engineer",
              ("HVAC Technician", "hvac,ventilation,refrigeration", "facilities", True)),
    "dana": ("dana.brooks@acme.inc", "Dana Brooks", "engineer",
             ("Maintenance Technician", "plumbing,furniture,general repairs", "facilities", True)),
    "eli": ("eli.nguyen@acme.inc", "Eli Nguyen", "engineer",
            ("Electrician", "power,lighting,wiring", "electrical", True)),
    "fiona": ("fiona.garcia@acme.inc", "Fiona Garcia", "engineer",
              ("Desktop Support Engineer", "network,hardware,printers", "it_support", True)),
    "gabe": ("gabe.thompson@acme.inc", "Gabe Thompson", "engineer",
             ("Network Engineer", "network,wi-fi,switching", "it_support", False)),
    "hana": ("hana.suzuki@acme.inc", "Hana Suzuki", "engineer",
             ("A/V Specialist", "video conferencing,displays,audio", "av", True)),
    "ivan": ("ivan.petrov@acme.inc", "Ivan Petrov", "engineer",
             ("Security Systems Technician", "badge readers,cameras,locks", "security", True)),
}

# building -> (address, {floor: [seats/rooms]})
FACILITIES: Dict[str, tuple] = {
    "HQ Tower": ("100 Main Street", {
        "Lobby": ["Reception", "Security Desk"],
        "2nd Floor": ["2-A01", "2-A02", "2-B10", "Print Room 2"],
        "3rd Floor": ["3-A12", "3-A14", "3-B05", "Boardroom 3A"],
        "4th Floor": ["4-C01", "4-C02", "Huddle Room 4B"],
    }),
    "Riverside Annex": ("200 Oak Avenue", {
        "Ground Floor": ["G-01", "G-02", "Kitchen"],
        "1st Floor": ["1-101", "1-102", "Training Room"],
    }),
    "Innovation Lab": ("5 Tech Park Drive", {
        "Main Floor": ["Lab Bench 1", "Lab Bench 2", "Demo Room"],
    }),
}

# Each incident: who reported it, where, and a list of steps (hours after creation, actor, action, value).
# Actors: a USERS key, or "reporter" / "assignee". Actions: assign, status (value=(status, reason)),
# note, escalate (value=reason), priority.
INCIDENTS: List[Dict[str, Any]] = [
    # --- Recurring HVAC issue at the same seat (hotspot + recurring list) -------------------------
    {"title": "Desk area far too hot in the afternoon", "category": "hvac", "priority": "medium",
     "where": ("HQ Tower", "3rd Floor", "3-A12"), "reporter": "jordan", "days_ago": 27,
     "description": "Temperature by the window desks climbs above 28°C after 2pm.",
     "steps": [(1, "admin", "assign", "chris"), (3, "chris", "status", ("in_progress", None)),
               (20, "chris", "status", ("resolved", "Rebalanced the VAV box damper for zone 3A.")),
               (30, "reporter", "status", ("closed", None))]},
    {"title": "Heat is back at 3-A12", "category": "hvac", "priority": "high",
     "where": ("HQ Tower", "3rd Floor", "3-A12"), "reporter": "jordan", "days_ago": 12,
     "description": "Same problem as last time - it's sweltering by 3pm again.",
     "steps": [(0.5, "admin", "assign", "chris"), (2, "chris", "status", ("in_progress", None)),
               (26, "chris", "status", ("resolved", "Replaced the faulty thermostat sensor for zone 3A.")),
               (50, "reporter", "status", ("closed", None))]},
    {"title": "3-A12 overheating a third time", "category": "hvac", "priority": "high",
     "where": ("HQ Tower", "3rd Floor", "3-A12"), "reporter": "jordan", "days_ago": 3,
     "description": "Third time this month. Can someone look at the whole zone this time?",
     "steps": [(0.3, "admin", "note", "Escalating internally - this is the third report for this seat."),
               (0.5, "admin", "assign", "chris"), (4, "chris", "status", ("in_progress", None)),
               (8, "chris", "status", ("blocked", "Rooftop unit compressor needs replacing - part ordered, ETA Friday.")),
               (9, "reporter", "note", "Thanks for the update. Is there a portable fan I can borrow meanwhile?"),
               (11, "chris", "note", "Dana is dropping one off at your desk this afternoon.")]},

    # --- Boardroom A/V: recurring + escalated critical ------------------------------------------
    {"title": "Boardroom display won't wake up", "category": "av_equipment", "priority": "medium",
     "where": ("HQ Tower", "3rd Floor", "Boardroom 3A"), "reporter": "priya", "days_ago": 22,
     "steps": [(1, "admin", "assign", "hana"), (2, "hana", "status", ("in_progress", None)),
               (5, "hana", "status", ("resolved", "Firmware update applied to the display controller.")),
               (6, "reporter", "status", ("closed", None))]},
    {"title": "No audio in Boardroom video calls", "category": "av_equipment", "priority": "high",
     "where": ("HQ Tower", "3rd Floor", "Boardroom 3A"), "reporter": "sam", "days_ago": 9,
     "steps": [(2, "admin", "assign", "hana"), (3, "hana", "status", ("in_progress", None)),
               (6, "hana", "status", ("resolved", "Speakerphone was muted at the DSP - unmuted and locked settings.")),
               (30, "admin", "status", ("closed", None))]},
    {"title": "Boardroom video conferencing completely down before board meeting", "category": "av_equipment",
     "priority": "critical", "where": ("HQ Tower", "3rd Floor", "Boardroom 3A"), "reporter": "priya", "days_ago": 0.25,
     "description": "Board meeting starts at 2pm - camera and display both show no signal.",
     "steps": [(0.1, "reporter", "escalate", "Board meeting at 2pm today with external investors."),
               (0.15, "admin", "assign", "hana"), (0.2, "hana", "status", ("in_progress", None)),
               (0.22, "hana", "note", "On my way up now - bringing a spare codec.")]},

    # --- Printers: recurring + reopened ----------------------------------------------------------
    {"title": "Printer on 2nd floor jams on every job", "category": "printer", "priority": "low",
     "where": ("HQ Tower", "2nd Floor", "Print Room 2"), "reporter": "taylor", "days_ago": 18,
     "steps": [(3, "admin", "assign", "fiona"), (20, "fiona", "status", ("in_progress", None)),
               (21, "fiona", "status", ("resolved", "Cleared paper path and replaced the pickup roller.")),
               (40, "reporter", "status", ("closed", None))]},
    {"title": "2nd floor printer showing offline", "category": "printer", "priority": "medium",
     "where": ("HQ Tower", "2nd Floor", "Print Room 2"), "reporter": "jordan", "days_ago": 5,
     "steps": [(2, "admin", "assign", "fiona"), (4, "fiona", "status", ("in_progress", None)),
               (5, "fiona", "status", ("resolved", "Printer had a stale IP lease - reassigned a static address.")),
               (22, "reporter", "status", ("open", "Still offline for everyone on the east side of the floor.")),
               (24, "fiona", "status", ("in_progress", None)),
               (25, "fiona", "note", "Looks like the east-side switch port is flapping. Checking with networking.")]},

    # --- Network: escalated, engineer unavailable, then reassigned -------------------------------
    {"title": "Wi-Fi drops every few minutes on 4th floor", "category": "network", "priority": "high",
     "where": ("HQ Tower", "4th Floor", None), "reporter": "sam", "days_ago": 2,
     "description": "Whole floor is affected - video calls keep disconnecting.",
     "steps": [(1, "admin", "assign", "gabe"),
               (20, "reporter", "escalate", "Entire floor affected for a day and no update yet."),
               (21, "admin", "assign", "fiona"),
               (21.5, "admin", "note", "Gabe is out this week - reassigned to Fiona."),
               (22, "fiona", "status", ("in_progress", None)),
               (23, "fiona", "note", "Access point 4-AP3 is rebooting in a loop. Replacing it now.")]},
    {"title": "Ethernet port dead at desk 4-C02", "category": "network", "priority": "medium",
     "where": ("HQ Tower", "4th Floor", "4-C02"), "reporter": "taylor", "days_ago": 15,
     "steps": [(2, "admin", "assign", "fiona"), (3, "fiona", "status", ("in_progress", None)),
               (4, "fiona", "status", ("resolved", "Re-patched the port in the 4th floor comms room.")),
               (6, "reporter", "status", ("closed", None))]},

    # --- Security: blocked waiting on vendor -------------------------------------------------------
    {"title": "Badge reader at Annex side entrance not working", "category": "access_security", "priority": "high",
     "where": ("Riverside Annex", "Ground Floor", None), "reporter": "priya", "days_ago": 4,
     "steps": [(1, "admin", "assign", "ivan"), (2, "ivan", "status", ("in_progress", None)),
               (5, "ivan", "status", ("blocked", "Controller board failed - waiting on the access-control vendor visit.")),
               (6, "ivan", "note", "Side entrance is propped with a guard posted until the vendor arrives.")]},

    # --- Electrical --------------------------------------------------------------------------------
    {"title": "Flickering lights in Training Room", "category": "lighting", "priority": "low",
     "where": ("Riverside Annex", "1st Floor", "Training Room"), "reporter": "sam", "days_ago": 20,
     "steps": [(5, "admin", "assign", "eli"), (30, "eli", "status", ("in_progress", None)),
               (31, "eli", "status", ("resolved", "Replaced two failing LED drivers.")),
               (48, "reporter", "status", ("closed", None))]},
    {"title": "Power strip sparking at Lab Bench 2", "category": "electrical", "priority": "critical",
     "where": ("Innovation Lab", "Main Floor", "Lab Bench 2"), "reporter": "taylor", "days_ago": 6,
     "steps": [(0.2, "admin", "assign", "eli"), (0.3, "eli", "status", ("in_progress", None)),
               (1, "eli", "status", ("resolved", "Removed the damaged strip and tested the circuit - safe to use.")),
               (3, "reporter", "status", ("closed", None))]},
    {"title": "Several outlets dead in Demo Room", "category": "electrical", "priority": "medium",
     "where": ("Innovation Lab", "Main Floor", "Demo Room"), "reporter": "priya", "days_ago": 1,
     "steps": [(2, "admin", "assign", "eli"), (3, "eli", "status", ("in_progress", None))]},
    {"title": "Lobby lights on a timer shut off too early", "category": "lighting", "priority": "low",
     "where": ("HQ Tower", "Lobby", "Reception"), "reporter": "sam", "days_ago": 8,
     "steps": [(4, "admin", "assign", "eli")]},

    # --- Facilities: plumbing / cleaning / furniture ------------------------------------------------
    {"title": "Leak under the kitchen sink", "category": "plumbing", "priority": "high",
     "where": ("Riverside Annex", "Ground Floor", "Kitchen"), "reporter": "taylor", "days_ago": 14,
     "steps": [(1, "admin", "assign", "dana"), (2, "dana", "status", ("in_progress", None)),
               (4, "dana", "status", ("resolved", "Tightened the compression fitting and replaced the trap seal.")),
               (24, "reporter", "status", ("closed", None))]},
    {"title": "Kitchen sink leaking again", "category": "plumbing", "priority": "medium",
     "where": ("Riverside Annex", "Ground Floor", "Kitchen"), "reporter": "sam", "days_ago": 3.5,
     "description": "Small puddle forming under the cabinet again.",
     "steps": []},  # unassigned and untouched for days -> shows as stale
    {"title": "Broken chair at 2-A01", "category": "furniture", "priority": "low",
     "where": ("HQ Tower", "2nd Floor", "2-A01"), "reporter": "jordan", "days_ago": 1.5,
     "description": "Gas lift is gone - chair sinks to the lowest height.",
     "steps": [(3, "admin", "assign", "dana"), (5, "dana", "status", ("in_progress", None)),
               (6, "dana", "status", ("resolved", "Swapped in a new chair from storage. Old one tagged for disposal."))]},
    {"title": "Sit-stand desk stuck at lowest height", "category": "furniture", "priority": "medium",
     "where": ("HQ Tower", "3rd Floor", "3-B05"), "reporter": "priya", "days_ago": 10,
     "steps": [(6, "admin", "assign", "dana"), (8, "dana", "status", ("in_progress", None)),
               (9, "dana", "status", ("resolved", "Reset the desk controller and recalibrated the motors.")),
               (30, "admin", "status", ("closed", None))]},
    {"title": "Spill on carpet near 4-C01", "category": "cleaning", "priority": "low",
     "where": ("HQ Tower", "4th Floor", "4-C01"), "reporter": "taylor", "days_ago": 0.1,
     "steps": []},

    # --- Chris's pile-up (heavy workload demo) ----------------------------------------------------
    {"title": "Server room temperature alarm", "category": "hvac", "priority": "critical",
     "where": ("Innovation Lab", "Main Floor", None), "reporter": "taylor", "days_ago": 0.5,
     "steps": [(0.1, "admin", "assign", "chris"), (0.3, "chris", "status", ("in_progress", None))]},
    {"title": "Stuffy air in Training Room", "category": "hvac", "priority": "medium",
     "where": ("Riverside Annex", "1st Floor", "Training Room"), "reporter": "sam", "days_ago": 2.5,
     "steps": [(4, "admin", "assign", "chris")]},
    {"title": "AC vent dripping onto desk 2-B10", "category": "hvac", "priority": "high",
     "where": ("HQ Tower", "2nd Floor", "2-B10"), "reporter": "jordan", "days_ago": 1,
     "steps": [(1, "admin", "assign", "chris"),
               (2, "chris", "note", "Will get to this after the server room alarm - please move your laptop for now.")]},
    {"title": "Reception area too cold in the mornings", "category": "hvac", "priority": "low",
     "where": ("HQ Tower", "Lobby", "Reception"), "reporter": "priya", "days_ago": 6,
     "steps": [(10, "admin", "assign", "chris")]},

    # --- Brand-new, unassigned (for the assignment-suggestion demo) -------------------------------
    {"title": "Monitor flickering at 3-A14", "category": "hardware", "priority": "medium",
     "where": ("HQ Tower", "3rd Floor", "3-A14"), "reporter": "jordan", "days_ago": 0.05,
     "description": "Second monitor flickers every few seconds, tried a different cable already.",
     "steps": []},
    {"title": "Desk phone has no dial tone", "category": "phone", "priority": "low",
     "where": ("Riverside Annex", "1st Floor", "1-102"), "reporter": "taylor", "days_ago": 0.4,
     "steps": []},
    {"title": "Water cooler on 2nd floor empty for days", "category": "other", "priority": "low",
     "where": ("HQ Tower", "2nd Floor", None), "reporter": "sam", "days_ago": 0.8,
     "steps": []},
]


def _insert(cur: Any, sql: str, values: tuple) -> int:
    cur.execute(sql + " RETURNING id", values)
    return cur.fetchone()[0]


def demo_reset_enabled() -> bool:
    """Whether admins may reset to demo data from the app: in the cloud demo (SEED_DEMO_DATA) and locally."""
    return os.getenv("SEED_DEMO_DATA") == "true" or os.getenv("IS_LOCAL", "true") == "true"


def seed_if_empty() -> bool:
    """Seed demo data only if the app hasn't been used yet (no buildings and no incidents). Returns True if it seeded.

    Accounts created before any facility exists (e.g. a bootstrap admin) are replaced by the demo accounts.
    Holds a database lock for the whole check-and-seed, so if several Lambda instances start at once
    only one seeds; the others wait, then see the data and skip. Never runs once real data exists.
    """
    init_schema()
    conn = get_connection()
    with transaction(), conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (_SEED_LOCK_ID,))
        cur.execute("SELECT EXISTS (SELECT 1 FROM buildings) OR EXISTS (SELECT 1 FROM incidents)")
        if cur.fetchone()[0]:
            return False
        reset_and_seed(verbose=False)
    return True


def reset_and_seed(verbose: bool = True) -> None:
    """Delete everything and load the demo data. `verbose` prints the accounts (CLI use only)."""
    init_schema()
    now = datetime.now(timezone.utc)
    conn = get_connection()
    with transaction(), conn.cursor() as cur:
        cur.execute(
            "TRUNCATE incident_events, incident_notes, incidents, seats, floors, buildings, "
            "engineer_profiles, users RESTART IDENTITY CASCADE"
        )

        password_hash = hash_password(DEMO_PASSWORD)
        user_ids: Dict[str, int] = {}
        roles: Dict[str, str] = {}
        names: Dict[int, str] = {}
        for key, (email, full_name, role, profile) in USERS.items():
            user_id = _insert(
                cur,
                "INSERT INTO users (email, password_hash, full_name, role, created_at) VALUES (%s, %s, %s, %s, %s)",
                (email, password_hash, full_name, role, now - timedelta(days=45)),
            )
            user_ids[key], roles[key], names[user_id] = user_id, role, full_name
            if profile:
                title, skills, department, available = profile
                cur.execute(
                    "INSERT INTO engineer_profiles (user_id, title, skills, department, is_available) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (user_id, title, skills, department, available),
                )

        locations: Dict[tuple, int] = {}
        for building, (address, floors) in FACILITIES.items():
            building_id = _insert(cur, "INSERT INTO buildings (name, address) VALUES (%s, %s)", (building, address))
            locations[(building,)] = building_id
            for floor, seats in floors.items():
                floor_id = _insert(cur, "INSERT INTO floors (building_id, name) VALUES (%s, %s)", (building_id, floor))
                locations[(building, floor)] = floor_id
                for seat in seats:
                    locations[(building, floor, seat)] = _insert(
                        cur, "INSERT INTO seats (floor_id, label) VALUES (%s, %s)", (floor_id, seat)
                    )

        for spec in INCIDENTS:
            _seed_incident(cur, spec, now, user_ids, roles, names, locations)

    if not verbose:  # Lambda: never write the password to CloudWatch logs
        return
    print(f"Seeded {len(USERS)} users, {len(FACILITIES)} buildings, {len(INCIDENTS)} incidents.\n")
    print(f"All accounts use the password: {DEMO_PASSWORD}\n")
    for email, full_name, role, profile in USERS.values():
        extra = f" ({profile[2]}{'' if profile[3] else ', unavailable'})" if profile else ""
        print(f"  {role:<15} {email:<26} {full_name}{extra}")


def _seed_incident(
    cur: Any,
    spec: Dict[str, Any],
    now: datetime,
    user_ids: Dict[str, int],
    roles: Dict[str, str],
    names: Dict[int, str],
    locations: Dict[tuple, int],
) -> None:
    """Insert an incident, then replay its steps through the workflow rules with backdated timestamps."""
    created = now - timedelta(days=spec["days_ago"])
    building, floor, seat = spec["where"]
    incident: Dict[str, Any] = {
        "title": spec["title"], "description": spec.get("description"), "category": spec["category"],
        "priority": spec["priority"], "status": "open", "assigned_to": None,
        "is_escalated": False, "escalation_reason": None, "blocked_reason": None,
        "building_id": locations[(building,)],
        "floor_id": locations[(building, floor)] if floor else None,
        "seat_id": locations[(building, floor, seat)] if seat else None,
        "reported_by": user_ids[spec["reporter"]],
    }
    milestones: Dict[str, Optional[datetime]] = {
        key: None for key in ("acknowledged_at", "assigned_at", "started_at", "resolved_at", "closed_at")
    }
    events: List[tuple] = [(created, incident["reported_by"], "created", None, "open", None)]
    notes: List[tuple] = []
    updated = created

    for hours, actor_key, action, value in spec["steps"]:
        at = created + timedelta(hours=hours)
        if actor_key == "reporter":
            actor_key = spec["reporter"]
        elif actor_key == "assignee":
            actor_key = next(k for k, v in user_ids.items() if v == incident["assigned_to"])
        actor_id, actor_role = user_ids[actor_key], roles[actor_key]

        if action == "note":
            notes.append((at, actor_id, value))
            events.append((at, actor_id, "note_added", None, None, None))
            if actor_role in workflow.STAFF_ROLES and milestones["acknowledged_at"] is None:
                milestones["acknowledged_at"] = at
            continue

        reason = None
        if action == "assign":
            changes: Dict[str, Any] = {"assigned_to": user_ids[value]}
        elif action == "escalate":
            changes = {"is_escalated": True, "escalation_reason": value}
        elif action == "priority":
            changes = {"priority": value}
        else:  # status
            new_status, reason = value
            workflow.validate_transition(actor_role, incident["status"], new_status)
            changes = {"status": new_status}
            if new_status == "blocked":
                changes["blocked_reason"] = reason
            elif incident["status"] == "blocked":
                changes["blocked_reason"] = None

        for column, mode in workflow.milestone_updates(incident, changes, actor_role).items():
            if mode == "set" or (mode == "set_if_null" and milestones[column] is None):
                milestones[column] = at
            elif mode == "clear":
                milestones[column] = None
        for event in workflow.change_events(incident, changes, reason, lambda uid: names.get(uid)):
            events.append((at, actor_id, event["event_type"], event["from_value"], event["to_value"], event["details"]))
        if reason:
            notes.append((at, actor_id, workflow.status_note(incident["status"], changes["status"], reason)))
        incident.update(changes)
        updated = at

    incident_id = _insert(
        cur,
        """
        INSERT INTO incidents (title, description, category, status, priority, building_id, floor_id, seat_id,
            reported_by, assigned_to, is_escalated, escalation_reason, blocked_reason, created_at, updated_at,
            acknowledged_at, assigned_at, started_at, resolved_at, closed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            incident["title"], incident["description"], incident["category"], incident["status"],
            incident["priority"], incident["building_id"], incident["floor_id"], incident["seat_id"],
            incident["reported_by"], incident["assigned_to"], incident["is_escalated"],
            incident["escalation_reason"], incident["blocked_reason"], created, updated,
            milestones["acknowledged_at"], milestones["assigned_at"], milestones["started_at"],
            milestones["resolved_at"], milestones["closed_at"],
        ),
    )
    for at, actor_id, event_type, from_value, to_value, details in events:
        cur.execute(
            "INSERT INTO incident_events (incident_id, actor_id, event_type, from_value, to_value, details, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (incident_id, actor_id, event_type, from_value, to_value, details, at),
        )
    for at, author_id, message in notes:
        cur.execute(
            "INSERT INTO incident_notes (incident_id, author_id, message, created_at) VALUES (%s, %s, %s, %s)",
            (incident_id, author_id, message, at),
        )


if __name__ == "__main__":
    if "--yes" not in sys.argv:
        sys.exit("This DELETES all data in the configured database. Re-run with --yes to confirm.")
    reset_and_seed()
