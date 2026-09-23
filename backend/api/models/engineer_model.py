"""Data access layer for engineer profiles and workload."""
from typing import Any, Dict, List, Optional

from db import get_connection, row_to_dict, rows_to_dicts

_PROFILE_FIELDS = {"title", "skills", "department", "is_available"}

_PROFILE_SELECT = """
    SELECT u.id AS user_id, u.email, u.full_name, p.title, p.skills, p.department, p.is_available, p.created_at
    FROM engineer_profiles p
    JOIN users u ON u.id = p.user_id
"""


def create_profile(
    user_id: int, title: Optional[str], skills: Optional[str], department: Optional[str], is_available: bool
) -> Dict[str, Any]:
    """Insert an engineer profile linked to an existing user account."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO engineer_profiles (user_id, title, skills, department, is_available)
            VALUES (%s, %s, %s, %s, %s) RETURNING *
            """,
            (user_id, title, skills, department, is_available),
        )
        return row_to_dict(cur, cur.fetchone())


def list_profiles() -> List[Dict[str, Any]]:
    """List all engineer profiles joined with their user details."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"{_PROFILE_SELECT} ORDER BY u.full_name")
        return rows_to_dicts(cur, cur.fetchall())


def get_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single engineer profile by user id."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"{_PROFILE_SELECT} WHERE u.id = %s", (user_id,))
        return row_to_dict(cur, cur.fetchone())


def update_profile(user_id: int, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update whitelisted fields (title, skills, department, availability) on an engineer profile."""
    fields = [field for field in _PROFILE_FIELDS if field in changes]
    if not fields:
        return get_profile(user_id)

    set_clause = ", ".join(f"{field} = %s" for field in fields)
    values = [changes[field] for field in fields] + [user_id]

    conn = get_connection()
    with conn.cursor() as cur:
        # nosec: `fields` are drawn only from the _PROFILE_FIELDS allow-list, never raw user input.
        cur.execute(f"UPDATE engineer_profiles SET {set_clause} WHERE user_id = %s", values)
        if cur.rowcount == 0:
            return None
    return get_profile(user_id)


def list_workload() -> List[Dict[str, Any]]:
    """Per-engineer ticket counts: active/in-progress/blocked/urgent now, plus recent throughput."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                u.id AS user_id, u.email, u.full_name, p.title, p.skills, p.department, p.is_available,
                COUNT(i.id) FILTER (WHERE i.status IN ('open', 'in_progress', 'blocked')) AS active_count,
                COUNT(i.id) FILTER (WHERE i.status = 'open') AS open_count,
                COUNT(i.id) FILTER (WHERE i.status = 'in_progress') AS in_progress_count,
                COUNT(i.id) FILTER (WHERE i.status = 'blocked') AS blocked_count,
                COUNT(i.id) FILTER (
                    WHERE i.status IN ('open', 'in_progress', 'blocked') AND i.priority IN ('high', 'critical')
                ) AS urgent_count,
                COUNT(i.id) FILTER (WHERE i.resolved_at >= now() - interval '30 days') AS resolved_30d,
                ROUND((AVG(EXTRACT(EPOCH FROM (i.resolved_at - i.created_at)))
                    FILTER (WHERE i.resolved_at IS NOT NULL) / 3600)::numeric, 1) AS avg_resolve_hours
            FROM engineer_profiles p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN incidents i ON i.assigned_to = u.id AND NOT i.is_archived
            GROUP BY u.id, u.email, u.full_name, p.title, p.skills, p.department, p.is_available
            ORDER BY u.full_name
            """
        )
        rows = rows_to_dicts(cur, cur.fetchall())
    for row in rows:
        if row["avg_resolve_hours"] is not None:
            row["avg_resolve_hours"] = float(row["avg_resolve_hours"])
    return rows
