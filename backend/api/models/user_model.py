"""Data access layer for users and authentication."""
from typing import Any, Dict, List, Optional

from db import get_connection, row_to_dict, rows_to_dicts


def create_user(email: str, password_hash: str, full_name: str, role: str) -> Dict[str, Any]:
    """Insert a new user and return the created record (excluding password hash)."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (email, password_hash, full_name, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id, email, full_name, role, created_at
            """,
            (email, password_hash, full_name, role),
        )
        return row_to_dict(cur, cur.fetchone())


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve a user by email, including the password hash (for login verification)."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, full_name, role, created_at FROM users WHERE email = %s",
            (email,),
        )
        return row_to_dict(cur, cur.fetchone())


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a user by id (excluding password hash)."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, full_name, role, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        return row_to_dict(cur, cur.fetchone())


def list_users(role: Optional[str] = None) -> List[Dict[str, Any]]:
    """List users, optionally filtered by role."""
    conn = get_connection()
    with conn.cursor() as cur:
        if role:
            cur.execute(
                "SELECT id, email, full_name, role, created_at FROM users WHERE role = %s ORDER BY id",
                (role,),
            )
        else:
            cur.execute("SELECT id, email, full_name, role, created_at FROM users ORDER BY id")
        return rows_to_dicts(cur, cur.fetchall())


def delete_user(user_id: int) -> bool:
    """Delete a user by id. Cascades to their engineer profile, if any."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        return cur.rowcount > 0


def any_admin_exists() -> bool:
    """Return True if at least one facility_admin user already exists (bootstrap check)."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE role = 'facility_admin' LIMIT 1")
        return cur.fetchone() is not None
