"""Data access layer for incident tickets."""
from typing import Any, Dict, List, Optional

from db import get_connection, row_to_dict, rows_to_dicts

_UPDATABLE_FIELDS = {
    "title", "description", "category", "priority", "status",
    "assigned_to", "is_escalated", "escalation_reason", "blocked_reason",
    "building_id", "floor_id", "seat_id",
}
_EQUALITY_FILTERS = ("priority", "category", "building_id", "assigned_to", "reported_by")
_MILESTONE_COLUMNS = {"acknowledged_at", "assigned_at", "started_at", "resolved_at", "closed_at"}
_MILESTONE_SQL = {
    "set": "{column} = now()",
    "set_if_null": "{column} = COALESCE({column}, now())",
    "clear": "{column} = NULL",
}
_SORTS = {
    "newest": "i.created_at DESC",
    "oldest": "i.created_at ASC",
    "updated": "last_activity_at DESC",
    "priority": (
        "CASE i.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, "
        "i.created_at ASC"
    ),
}

# Incidents joined with human-readable location/people names and their latest activity time.
_INCIDENT_SELECT = """
    SELECT
        i.*,
        b.name AS building_name,
        f.name AS floor_name,
        s.label AS seat_label,
        r.full_name AS reporter_name,
        a.full_name AS assignee_name,
        GREATEST(
            i.updated_at,
            (SELECT MAX(e.created_at) FROM incident_events e WHERE e.incident_id = i.id)
        ) AS last_activity_at,
        (SELECT COUNT(*) FROM incident_notes n WHERE n.incident_id = i.id) AS note_count
    FROM incidents i
    LEFT JOIN buildings b ON b.id = i.building_id
    LEFT JOIN floors f ON f.id = i.floor_id
    LEFT JOIN seats s ON s.id = i.seat_id
    LEFT JOIN users r ON r.id = i.reported_by
    LEFT JOIN users a ON a.id = i.assigned_to
"""


def create_incident(
    title: str,
    description: Optional[str],
    category: str,
    priority: str,
    building_id: int,
    floor_id: Optional[int],
    seat_id: Optional[int],
    reported_by: int,
) -> Dict[str, Any]:
    """Insert a new incident with the default 'open' status, returning the joined record."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO incidents
                (title, description, category, priority, building_id, floor_id, seat_id, reported_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (title, description, category, priority, building_id, floor_id, seat_id, reported_by),
        )
        incident_id = cur.fetchone()[0]
    return get_incident(incident_id)


def get_incident(incident_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single incident by id, joined with location/people names."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"{_INCIDENT_SELECT} WHERE i.id = %s", (incident_id,))
        return row_to_dict(cur, cur.fetchone())


def list_incidents(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List incidents matching the given filters (all optional).

    Supported filters: status (list), priority, category, building_id, assigned_to, reported_by,
    escalated (bool), unassigned (bool), archived (bool: only archived incidents instead of only live ones),
    search (text or '#id'), sort (newest/oldest/updated/priority).
    """
    clauses = ["i.is_archived" if filters.get("archived") else "NOT i.is_archived"]
    values: List[Any] = []

    if filters.get("status"):
        clauses.append("i.status = ANY(%s)")
        values.append(list(filters["status"]))

    for field in _EQUALITY_FILTERS:
        if filters.get(field) is not None:
            clauses.append(f"i.{field} = %s")
            values.append(filters[field])

    if filters.get("escalated"):
        clauses.append("i.is_escalated")
    if filters.get("unassigned"):
        clauses.append("i.assigned_to IS NULL")

    search = (filters.get("search") or "").strip()
    if search:
        term = f"%{search}%"
        search_clause = "(i.title ILIKE %s OR i.description ILIKE %s OR i.category ILIKE %s"
        values.extend([term, term, term])
        if search.lstrip("#").isdigit():
            search_clause += " OR i.id = %s"
            values.append(int(search.lstrip("#")))
        clauses.append(search_clause + ")")

    where_clause = f"WHERE {' AND '.join(clauses)}"
    order_by = _SORTS.get(filters.get("sort") or "newest", _SORTS["newest"])
    conn = get_connection()
    with conn.cursor() as cur:
        # nosec: filter columns and ORDER BY come only from the allow-lists above.
        cur.execute(f"{_INCIDENT_SELECT} {where_clause} ORDER BY {order_by}", values)
        return rows_to_dicts(cur, cur.fetchall())


def update_incident(incident_id: int, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update whitelisted incident fields and refresh updated_at."""
    fields = [field for field in _UPDATABLE_FIELDS if field in changes]
    if not fields:
        return get_incident(incident_id)

    set_clause = ", ".join(f"{field} = %s" for field in fields)
    values = [changes[field] for field in fields] + [incident_id]

    conn = get_connection()
    with conn.cursor() as cur:
        # nosec: `fields` are drawn only from the _UPDATABLE_FIELDS allow-list, never raw user input.
        cur.execute(f"UPDATE incidents SET {set_clause}, updated_at = now() WHERE id = %s", values)
        if cur.rowcount == 0:
            return None
    return get_incident(incident_id)


def apply_milestones(incident_id: int, milestones: Dict[str, str]) -> None:
    """Stamp/clear lifecycle timestamps, e.g. {'started_at': 'set_if_null', 'closed_at': 'clear'}."""
    assignments = [
        _MILESTONE_SQL[action].format(column=column)
        for column, action in milestones.items()
        if column in _MILESTONE_COLUMNS and action in _MILESTONE_SQL
    ]
    if not assignments:
        return
    conn = get_connection()
    with conn.cursor() as cur:
        # nosec: columns and SQL fragments come only from the allow-lists above.
        cur.execute(f"UPDATE incidents SET {', '.join(assignments)} WHERE id = %s", (incident_id,))


def delete_incident(incident_id: int) -> bool:
    """Delete an incident by id."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM incidents WHERE id = %s", (incident_id,))
        return cur.rowcount > 0
