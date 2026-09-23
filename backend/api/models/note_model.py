"""Data access layer for incident notes."""
from typing import Any, Dict, List, Optional

from db import get_connection, row_to_dict, rows_to_dicts

_NOTE_SELECT = """
    SELECT n.*, u.full_name AS author_name, u.role AS author_role
    FROM incident_notes n
    LEFT JOIN users u ON u.id = n.author_id
"""


def create_note(incident_id: int, author_id: int, message: str) -> Dict[str, Any]:
    """Insert a new note on an incident, returning it with author details."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO incident_notes (incident_id, author_id, message) VALUES (%s, %s, %s) RETURNING id",
            (incident_id, author_id, message),
        )
        note_id = cur.fetchone()[0]
    return get_note(note_id)


def list_notes(incident_id: int) -> List[Dict[str, Any]]:
    """List notes for an incident, oldest first, with author details."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"{_NOTE_SELECT} WHERE n.incident_id = %s ORDER BY n.created_at, n.id", (incident_id,))
        return rows_to_dicts(cur, cur.fetchall())


def get_note(note_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single note by id, with author details."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"{_NOTE_SELECT} WHERE n.id = %s", (note_id,))
        return row_to_dict(cur, cur.fetchone())


def delete_note(note_id: int) -> bool:
    """Delete a note by id."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM incident_notes WHERE id = %s", (note_id,))
        return cur.rowcount > 0
