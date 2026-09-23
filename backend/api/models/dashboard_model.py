"""Reporting queries behind the role-scoped dashboard.

Every query accepts a `scope` dict ({'reported_by': id} or {'assigned_to': id}, or {} for everything)
so employees and engineers see the same metrics restricted to their own tickets.
"""
from typing import Any, Dict, List, Optional, Tuple

from db import get_connection, row_to_dict, rows_to_dicts

ACTIVE = "('open', 'in_progress', 'blocked')"
STALE_AFTER_HOURS = 48

# milestone name -> timestamp column measured from incident creation
_MILESTONES = {
    "acknowledge": "acknowledged_at",
    "assign": "assigned_at",
    "start": "started_at",
    "resolve": "resolved_at",
}
_PRIORITY_ORDER = "CASE i.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"


def _scope(scope: Dict[str, Any], alias: str = "i") -> Tuple[List[str], List[Any]]:
    """Translate a scope dict into SQL conditions (on an allow-listed column) and bind values.

    Archived incidents (whose location was archived) are always excluded from reporting.
    """
    conditions, values = [f"NOT {alias}.is_archived"], []
    for field in ("reported_by", "assigned_to"):
        if scope.get(field) is not None:
            conditions.append(f"{alias}.{field} = %s")
            values.append(scope[field])
    return conditions, values


def _where(conditions: List[str]) -> str:
    return f"WHERE {' AND '.join(conditions)}" if conditions else ""


def _query(sql: str, values: List[Any]) -> List[Dict[str, Any]]:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(sql, values)
        return rows_to_dicts(cur, cur.fetchall())


def _query_one(sql: str, values: List[Any]) -> Dict[str, Any]:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(sql, values)
        return row_to_dict(cur, cur.fetchone()) or {}


def _to_float(value: Any) -> Optional[float]:
    return None if value is None else round(float(value), 1)


def kpis(scope: Dict[str, Any]) -> Dict[str, int]:
    """Headline counts: active, unassigned, escalated, blocked, and resolved in the last 7 days."""
    conditions, values = _scope(scope)
    return _query_one(
        f"""
        SELECT
            COUNT(*) FILTER (WHERE i.status IN {ACTIVE}) AS active,
            COUNT(*) FILTER (WHERE i.status IN {ACTIVE} AND i.assigned_to IS NULL) AS unassigned,
            COUNT(*) FILTER (WHERE i.status IN {ACTIVE} AND i.is_escalated) AS escalated,
            COUNT(*) FILTER (WHERE i.status = 'blocked') AS blocked,
            COUNT(*) FILTER (WHERE i.resolved_at >= now() - interval '7 days') AS resolved_7d,
            COUNT(*) AS total
        FROM incidents i {_where(conditions)}
        """,
        values,
    )


def count_by(column: str, scope: Dict[str, Any]) -> Dict[str, int]:
    """Incident counts grouped by status or priority."""
    if column not in ("status", "priority"):
        raise ValueError(f"Column '{column}' is not groupable")
    conditions, values = _scope(scope)
    rows = _query(f"SELECT i.{column} AS key, COUNT(*) AS count FROM incidents i {_where(conditions)} GROUP BY 1", values)
    return {row["key"]: row["count"] for row in rows}


def by_category(scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Incident counts per category (total and still active), most common first."""
    conditions, values = _scope(scope)
    return _query(
        f"""
        SELECT i.category, COUNT(*) AS count, COUNT(*) FILTER (WHERE i.status IN {ACTIVE}) AS active
        FROM incidents i {_where(conditions)}
        GROUP BY i.category ORDER BY count DESC, i.category
        """,
        values,
    )


def by_assignee() -> List[Dict[str, Any]]:
    """Active incident counts per assignee (null assignee = unassigned)."""
    return _query(
        f"""
        SELECT i.assigned_to AS assignee_id, u.full_name AS assignee_name, COUNT(*) AS count
        FROM incidents i LEFT JOIN users u ON u.id = i.assigned_to
        WHERE i.status IN {ACTIVE} AND NOT i.is_archived
        GROUP BY i.assigned_to, u.full_name ORDER BY count DESC
        """,
        [],
    )


def response_times(scope: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Average and median hours from report to each milestone (acknowledge/assign/start/resolve)."""
    conditions, values = _scope(scope)
    selects = []
    for name, column in _MILESTONES.items():
        seconds = f"EXTRACT(EPOCH FROM (i.{column} - i.created_at))::float8"
        selects.append(f"AVG({seconds}) / 3600 AS {name}_avg")
        selects.append(f"percentile_cont(0.5) WITHIN GROUP (ORDER BY {seconds}) / 3600 AS {name}_median")
        selects.append(f"COUNT(i.{column}) AS {name}_count")
    # nosec: column names come only from the fixed _MILESTONES mapping.
    row = _query_one(f"SELECT {', '.join(selects)} FROM incidents i {_where(conditions)}", values)
    return {
        name: {
            "avg_hours": _to_float(row.get(f"{name}_avg")),
            "median_hours": _to_float(row.get(f"{name}_median")),
            "count": row.get(f"{name}_count", 0),
        }
        for name in _MILESTONES
    }


def hotspots() -> Dict[str, List[Dict[str, Any]]]:
    """Top buildings, floors and seats by incident volume, plus recurring category+location pairs."""
    active = f"COUNT(i.id) FILTER (WHERE i.status IN {ACTIVE}) AS active"
    buildings = _query(
        f"""
        SELECT b.id, b.name AS label, NULL AS parent, COUNT(i.id) AS total, {active}
        FROM incidents i JOIN buildings b ON b.id = i.building_id
        WHERE NOT i.is_archived
        GROUP BY b.id, b.name ORDER BY total DESC, active DESC LIMIT 5
        """,
        [],
    )
    floors = _query(
        f"""
        SELECT f.id, f.name AS label, b.name AS parent, COUNT(i.id) AS total, {active}
        FROM incidents i JOIN floors f ON f.id = i.floor_id JOIN buildings b ON b.id = f.building_id
        WHERE NOT i.is_archived
        GROUP BY f.id, f.name, b.name ORDER BY total DESC, active DESC LIMIT 5
        """,
        [],
    )
    seats = _query(
        f"""
        SELECT s.id, s.label AS label, b.name || ' / ' || f.name AS parent, COUNT(i.id) AS total, {active}
        FROM incidents i
        JOIN seats s ON s.id = i.seat_id JOIN floors f ON f.id = s.floor_id JOIN buildings b ON b.id = f.building_id
        WHERE NOT i.is_archived
        GROUP BY s.id, s.label, b.name, f.name ORDER BY total DESC, active DESC LIMIT 5
        """,
        [],
    )
    recurring = _query(
        """
        SELECT
            i.category, b.name AS building_name, f.name AS floor_name, s.label AS seat_label,
            COUNT(*) AS count, MAX(i.created_at) AS last_reported_at
        FROM incidents i
        LEFT JOIN buildings b ON b.id = i.building_id
        LEFT JOIN floors f ON f.id = i.floor_id
        LEFT JOIN seats s ON s.id = i.seat_id
        WHERE NOT i.is_archived
        GROUP BY i.category, i.building_id, i.floor_id, i.seat_id, b.name, f.name, s.label
        HAVING COUNT(*) >= 2
        ORDER BY count DESC, last_reported_at DESC LIMIT 8
        """,
        [],
    )
    return {"buildings": buildings, "floors": floors, "seats": seats, "recurring": recurring}


def needs_attention(scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Active incidents that are escalated or blocked, with their reasons, most urgent first."""
    conditions, values = _scope(scope)
    conditions = [f"i.status IN {ACTIVE}", "(i.is_escalated OR i.status = 'blocked')", *conditions]
    return _query(
        f"""
        SELECT
            i.id, i.title, i.status, i.priority, i.category, i.is_escalated, i.escalation_reason,
            i.blocked_reason, i.created_at, u.full_name AS assignee_name, b.name AS building_name
        FROM incidents i
        LEFT JOIN users u ON u.id = i.assigned_to
        LEFT JOIN buildings b ON b.id = i.building_id
        {_where(conditions)}
        ORDER BY {_PRIORITY_ORDER}, i.created_at LIMIT 10
        """,
        values,
    )


def communication(scope: Dict[str, Any]) -> Dict[str, Any]:
    """How well reporters are kept informed: staff replies, first-response time, stale tickets, reopens."""
    conditions, values = _scope(scope)
    row = _query_one(
        f"""
        WITH scoped AS (SELECT i.* FROM incidents i {_where(conditions)}),
        first_staff_note AS (
            SELECT n.incident_id, MIN(n.created_at) AS first_at
            FROM incident_notes n JOIN scoped s ON s.id = n.incident_id
            WHERE n.author_id <> s.reported_by
            GROUP BY n.incident_id
        ),
        last_event AS (
            SELECT e.incident_id, MAX(e.created_at) AS last_at
            FROM incident_events e JOIN scoped s ON s.id = e.incident_id
            GROUP BY e.incident_id
        ),
        reopened AS (
            SELECT DISTINCT e.incident_id
            FROM incident_events e JOIN scoped s ON s.id = e.incident_id
            WHERE e.event_type = 'status_changed'
              AND e.from_value IN ('resolved', 'closed') AND e.to_value IN {ACTIVE}
        )
        SELECT
            COUNT(*) AS total,
            COUNT(fs.incident_id) AS with_staff_update,
            AVG(EXTRACT(EPOCH FROM (fs.first_at - s.created_at))::float8) / 3600 AS avg_first_response_hours,
            COUNT(*) FILTER (WHERE s.status IN ('resolved', 'closed')) AS finished,
            COUNT(*) FILTER (WHERE s.status IN ('resolved', 'closed') AND fs.incident_id IS NOT NULL)
                AS finished_with_update,
            COUNT(*) FILTER (
                WHERE s.status IN {ACTIVE}
                  AND GREATEST(s.updated_at, COALESCE(le.last_at, s.created_at))
                      < now() - interval '{STALE_AFTER_HOURS} hours'
            ) AS stale_active,
            (SELECT COUNT(*) FROM reopened) AS reopened
        FROM scoped s
        LEFT JOIN first_staff_note fs ON fs.incident_id = s.id
        LEFT JOIN last_event le ON le.incident_id = s.id
        """,
        values,
    )
    total = row.get("total") or 0
    finished = row.get("finished") or 0
    return {
        "total": total,
        "with_staff_update": row.get("with_staff_update") or 0,
        "staff_update_rate": round((row.get("with_staff_update") or 0) / total * 100) if total else None,
        "avg_first_response_hours": _to_float(row.get("avg_first_response_hours")),
        "finished": finished,
        "finished_with_update_rate": (
            round((row.get("finished_with_update") or 0) / finished * 100) if finished else None
        ),
        "stale_active": row.get("stale_active") or 0,
        "stale_after_hours": STALE_AFTER_HOURS,
        "reopened": row.get("reopened") or 0,
    }
