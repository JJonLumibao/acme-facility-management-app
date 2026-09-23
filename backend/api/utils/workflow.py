"""Incident workflow rules: allowed status transitions per role, milestone timestamps, and change events.

Everything here is pure (no database access) so the business rules can be unit-tested in isolation.
"""
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.validation import ValidationError

STATUSES = ("open", "in_progress", "blocked", "resolved", "closed")
ACTIVE_STATUSES = ("open", "in_progress", "blocked")
STAFF_ROLES = {"facility_admin", "engineer"}

STATUS_LABELS = {
    "open": "Open",
    "in_progress": "In Progress",
    "blocked": "Blocked",
    "resolved": "Resolved",
    "closed": "Closed",
}

# Full lifecycle, as allowed for facility admins.
_ADMIN_TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    "open": ("in_progress", "blocked", "resolved", "closed"),
    "in_progress": ("open", "blocked", "resolved"),
    "blocked": ("open", "in_progress", "resolved"),
    "resolved": ("open", "in_progress", "closed"),
    "closed": ("open",),
}

# Engineers work the ticket but cannot close it (closing confirms the outcome) or reopen closed tickets.
_ENGINEER_TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    "open": ("in_progress", "blocked", "resolved"),
    "in_progress": ("blocked", "resolved"),
    "blocked": ("in_progress", "resolved"),
    "resolved": ("in_progress",),
    "closed": (),
}

# Employees can only respond to a resolution: confirm it (close) or reopen it.
_EMPLOYEE_TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    "open": (),
    "in_progress": (),
    "blocked": (),
    "resolved": ("closed", "open"),
    "closed": (),
}

TRANSITIONS_BY_ROLE: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "facility_admin": _ADMIN_TRANSITIONS,
    "engineer": _ENGINEER_TRANSITIONS,
    "employee": _EMPLOYEE_TRANSITIONS,
}


def allowed_transitions(role: str, current_status: str) -> Tuple[str, ...]:
    """Return the statuses the given role may move an incident to from its current status."""
    return TRANSITIONS_BY_ROLE.get(role, {}).get(current_status, ())


def validate_transition(role: str, current_status: str, new_status: str) -> None:
    """Raise a ValidationError if the role may not move the incident between these statuses."""
    if new_status not in STATUSES:
        raise ValidationError("Invalid status", field="status")
    if new_status not in allowed_transitions(role, current_status):
        raise ValidationError(
            f"Cannot change status from {STATUS_LABELS[current_status]} to {STATUS_LABELS[new_status]}",
            field="status",
        )


def is_reopen(current_status: str, new_status: str) -> bool:
    """Return True when a finished (resolved/closed) incident is moved back into the active workflow."""
    return current_status in ("resolved", "closed") and new_status in ACTIVE_STATUSES


def requires_reason(current_status: str, new_status: str) -> bool:
    """Blocking, resolving and reopening must explain why, so the reporter stays informed."""
    return new_status in ("blocked", "resolved") or is_reopen(current_status, new_status)


def status_note(current_status: str, new_status: str, reason: str) -> str:
    """Build the note text posted to the incident thread when a status change carries a reason."""
    if is_reopen(current_status, new_status):
        prefix = "Reopened"
    else:
        prefix = {"blocked": "Blocked", "resolved": "Resolution"}.get(new_status, STATUS_LABELS[new_status])
    return f"{prefix}: {reason}"


def milestone_updates(
    incident: Dict[str, Any], changes: Dict[str, Any], actor_role: str
) -> Dict[str, str]:
    """Return milestone columns to update, mapped to an action: 'set_if_null', 'set' or 'clear'.

    - acknowledged_at: first time staff (admin/engineer) acts on the incident
    - assigned_at:     first time an engineer is assigned
    - started_at:      first time work starts (status -> in_progress)
    - resolved_at:     latest resolution (cleared when reopened)
    - closed_at:       latest closure (cleared when reopened)
    """
    updates: Dict[str, str] = {}
    if actor_role in STAFF_ROLES:
        updates["acknowledged_at"] = "set_if_null"
    if changes.get("assigned_to"):
        updates["assigned_at"] = "set_if_null"

    new_status = changes.get("status")
    if new_status and new_status != incident["status"]:
        if new_status == "in_progress":
            updates["started_at"] = "set_if_null"
        if new_status == "resolved":
            updates["resolved_at"] = "set"
        if new_status == "closed":
            updates["closed_at"] = "set"
            updates["resolved_at"] = "set_if_null"
        if is_reopen(incident["status"], new_status):
            updates["resolved_at"] = "clear"
            updates["closed_at"] = "clear"
    return updates


Event = Dict[str, Optional[str]]


def change_events(
    incident: Dict[str, Any],
    changes: Dict[str, Any],
    reason: Optional[str],
    resolve_user_name: Callable[[int], Optional[str]],
) -> List[Event]:
    """Describe each meaningful change as a timeline event (event_type, from_value, to_value, details)."""
    events: List[Event] = []

    def add(event_type: str, from_value: Any = None, to_value: Any = None, details: Optional[str] = None) -> None:
        events.append({
            "event_type": event_type,
            "from_value": None if from_value is None else str(from_value),
            "to_value": None if to_value is None else str(to_value),
            "details": details,
        })

    if "status" in changes and changes["status"] != incident["status"]:
        add("status_changed", incident["status"], changes["status"], reason or None)

    if "assigned_to" in changes and changes["assigned_to"] != incident.get("assigned_to"):
        previous = incident.get("assigned_to")
        new = changes["assigned_to"]
        previous_name = resolve_user_name(previous) if previous else None
        if new:
            add("assigned", previous_name, resolve_user_name(new))
        else:
            add("unassigned", previous_name, None)

    if "priority" in changes and changes["priority"] != incident["priority"]:
        add("priority_changed", incident["priority"], changes["priority"])

    if "is_escalated" in changes and bool(changes["is_escalated"]) != bool(incident["is_escalated"]):
        if changes["is_escalated"]:
            add("escalated", details=changes.get("escalation_reason") or incident.get("escalation_reason"))
        else:
            add("deescalated")

    edited = [
        field for field in ("title", "description", "category", "building_id", "floor_id", "seat_id")
        if field in changes and changes[field] != incident.get(field)
    ]
    if edited:
        add("details_updated", details=", ".join(field.replace("_id", "") for field in edited))

    return events
