"""Shared authorization helpers for incident-scoped resources."""
from typing import Any, Dict


def can_access_incident(user: Dict[str, Any], incident: Dict[str, Any]) -> bool:
    """Return True if the user may view or comment on the given incident."""
    if user["role"] == "facility_admin":
        return True
    if user["role"] == "engineer":
        return incident.get("assigned_to") == user["id"]
    return incident.get("reported_by") == user["id"]
