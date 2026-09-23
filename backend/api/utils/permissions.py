"""Shared authorization helpers for incident-scoped resources."""
from typing import Any, Dict


def can_access_incident(user: Dict[str, Any], incident: Dict[str, Any]) -> bool:
    """Return True if the user may view or comment on the given incident."""
    if user["role"] == "facility_admin":
        return True
    if user["role"] == "engineer":
        return incident.get("assigned_to") == user["id"]
    return incident.get("reported_by") == user["id"]


def report_scope(user: Dict[str, Any]) -> Dict[str, Any]:
    """Which incidents a user's reports cover: employees their own, engineers their assigned, admins all."""
    if user["role"] == "employee":
        return {"reported_by": user["id"]}
    if user["role"] == "engineer":
        return {"assigned_to": user["id"]}
    return {}
