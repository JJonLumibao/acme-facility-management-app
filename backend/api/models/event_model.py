"""Data access layer for the incident activity timeline (audit events)."""
from typing import Any, Dict, List, Optional

from db import get_connection, rows_to_dicts


def create_event(
    incident_id: int,
    actor_id: Optional[int],
    event_type: str,
    from_value: Optional[str] = None,
    to_value: Optional[str] = None,
    details: Optional[str] = None,
) -> None:
    """Record a single timeline event for an incident."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO incident_events (incident_id, actor_id, event_type, from_value, to_value, details)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (incident_id, actor_id, event_type, from_value, to_value, details),
        )


def list_events(incident_id: int) -> List[Dict[str, Any]]:
    """List an incident's timeline events, oldest first, with the actor's name and role."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.*, u.full_name AS actor_name, u.role AS actor_role
            FROM incident_events e
            LEFT JOIN users u ON u.id = e.actor_id
            WHERE e.incident_id = %s
            ORDER BY e.created_at, e.id
            """,
            (incident_id,),
        )
        return rows_to_dicts(cur, cur.fetchall())
