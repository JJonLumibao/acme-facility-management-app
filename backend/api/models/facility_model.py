"""Data access layer for buildings, floors, and seats."""
from typing import Any, Dict, List, Optional

from db import get_connection, row_to_dict, rows_to_dicts

_BUILDING_FIELDS = {"name", "address"}
_FLOOR_FIELDS = {"name"}
_SEAT_FIELDS = {"label"}

# Archiving cascades down the location tree and to every incident reported there; restoring reverses it.
# Each statement takes (is_archived, record_id).
_ARCHIVE_CASCADE = {
    "building": (
        "UPDATE buildings SET is_archived = %s WHERE id = %s",
        "UPDATE floors SET is_archived = %s WHERE building_id = %s",
        "UPDATE seats SET is_archived = %s WHERE floor_id IN (SELECT id FROM floors WHERE building_id = %s)",
        "UPDATE incidents SET is_archived = %s WHERE building_id = %s",
    ),
    "floor": (
        "UPDATE floors SET is_archived = %s WHERE id = %s",
        "UPDATE seats SET is_archived = %s WHERE floor_id = %s",
        "UPDATE incidents SET is_archived = %s WHERE floor_id = %s",
    ),
    "seat": (
        "UPDATE seats SET is_archived = %s WHERE id = %s",
        "UPDATE incidents SET is_archived = %s WHERE seat_id = %s",
    ),
}


def create_building(name: str, address: Optional[str]) -> Dict[str, Any]:
    """Insert a new building."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO buildings (name, address) VALUES (%s, %s) RETURNING *",
            (name, address),
        )
        return row_to_dict(cur, cur.fetchone())


def list_buildings(include_archived: bool = False) -> List[Dict[str, Any]]:
    """List buildings (archived ones only when requested)."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM buildings {'' if include_archived else 'WHERE NOT is_archived'} ORDER BY id")
        return rows_to_dicts(cur, cur.fetchall())


def get_building(building_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a building by id."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM buildings WHERE id = %s", (building_id,))
        return row_to_dict(cur, cur.fetchone())


def update_building(building_id: int, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update whitelisted fields on a building."""
    return _update("buildings", "id", building_id, changes, _BUILDING_FIELDS)


def delete_building(building_id: int) -> bool:
    """Delete a building by id."""
    return _delete("buildings", building_id)


def create_floor(building_id: int, name: str) -> Dict[str, Any]:
    """Insert a new floor under a building."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO floors (building_id, name) VALUES (%s, %s) RETURNING *",
            (building_id, name),
        )
        return row_to_dict(cur, cur.fetchone())


def list_floors(building_id: int, include_archived: bool = False) -> List[Dict[str, Any]]:
    """List floors within a building (archived ones only when requested)."""
    archived_clause = "" if include_archived else "AND NOT is_archived"
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM floors WHERE building_id = %s {archived_clause} ORDER BY id", (building_id,))
        return rows_to_dicts(cur, cur.fetchall())


def get_floor(floor_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a floor by id."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM floors WHERE id = %s", (floor_id,))
        return row_to_dict(cur, cur.fetchone())


def update_floor(floor_id: int, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update whitelisted fields on a floor."""
    return _update("floors", "id", floor_id, changes, _FLOOR_FIELDS)


def delete_floor(floor_id: int) -> bool:
    """Delete a floor by id."""
    return _delete("floors", floor_id)


def create_seat(floor_id: int, label: str) -> Dict[str, Any]:
    """Insert a new seat under a floor."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO seats (floor_id, label) VALUES (%s, %s) RETURNING *",
            (floor_id, label),
        )
        return row_to_dict(cur, cur.fetchone())


def list_seats(floor_id: int, include_archived: bool = False) -> List[Dict[str, Any]]:
    """List seats within a floor (archived ones only when requested)."""
    archived_clause = "" if include_archived else "AND NOT is_archived"
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM seats WHERE floor_id = %s {archived_clause} ORDER BY id", (floor_id,))
        return rows_to_dicts(cur, cur.fetchall())


def get_seat(seat_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a seat by id."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM seats WHERE id = %s", (seat_id,))
        return row_to_dict(cur, cur.fetchone())


def update_seat(seat_id: int, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update whitelisted fields on a seat."""
    return _update("seats", "id", seat_id, changes, _SEAT_FIELDS)


def delete_seat(seat_id: int) -> bool:
    """Delete a seat by id."""
    return _delete("seats", seat_id)


def set_archived(kind: str, record_id: int, is_archived: bool) -> None:
    """Archive or restore a building/floor/seat together with everything under it and its incidents."""
    conn = get_connection()
    with conn.cursor() as cur:
        for statement in _ARCHIVE_CASCADE[kind]:
            cur.execute(statement, (is_archived, record_id))


def _update(
    table: str, id_column: str, record_id: int, changes: Dict[str, Any], allowed_fields: set
) -> Optional[Dict[str, Any]]:
    """Update only whitelisted columns on a whitelisted table, returning the updated row."""
    fields = [field for field in allowed_fields if field in changes]
    if not fields:
        return _get(table, id_column, record_id)

    set_clause = ", ".join(f"{field} = %s" for field in fields)
    values = [changes[field] for field in fields] + [record_id]

    conn = get_connection()
    with conn.cursor() as cur:
        # nosec: `table`/`fields` are always fixed literals from this module, never raw user input.
        cur.execute(f"UPDATE {table} SET {set_clause} WHERE {id_column} = %s RETURNING *", values)
        row = cur.fetchone()
        return row_to_dict(cur, row) if row else None


def _get(table: str, id_column: str, record_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a row by id from a whitelisted table name."""
    conn = get_connection()
    with conn.cursor() as cur:
        # nosec: `table` is always a fixed literal from this module, never raw user input.
        cur.execute(f"SELECT * FROM {table} WHERE {id_column} = %s", (record_id,))
        return row_to_dict(cur, cur.fetchone())


def _delete(table: str, record_id: int) -> bool:
    """Delete a row by id from a whitelisted table name."""
    conn = get_connection()
    with conn.cursor() as cur:
        # nosec: `table` is always a fixed literal from this module, never raw user input.
        cur.execute(f"DELETE FROM {table} WHERE id = %s", (record_id,))
        return cur.rowcount > 0
