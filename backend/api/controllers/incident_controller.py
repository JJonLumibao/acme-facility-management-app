"""Business logic for facility incident tickets."""
from typing import Any, Dict, Optional

from db import transaction
from models import engineer_model, event_model, facility_model, incident_model, note_model, user_model
from utils import workflow
from utils.catalog import CATEGORY_KEYS
from utils.permissions import can_access_incident
from utils.responses import error, no_content, success
from utils.validation import ValidationError, require_fields

VALID_PRIORITIES = {"low", "medium", "high", "critical"}
_SORT_OPTIONS = {"newest", "oldest", "updated", "priority"}

_ADMIN_EDITABLE_FIELDS = (
    "title", "description", "category", "priority", "status", "assigned_to",
    "is_escalated", "escalation_reason", "building_id", "floor_id", "seat_id",
)
_ENGINEER_EDITABLE_FIELDS = ("status",)
_EMPLOYEE_EDITABLE_FIELDS = ("priority", "is_escalated", "escalation_reason", "status")


def _optional_int(value: Any, field: str) -> Optional[int]:
    """Parse an optional integer id from a payload/query value."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Invalid {field}", field=field) from exc


def _validate_location(building_id: Optional[int], floor_id: Optional[int], seat_id: Optional[int]) -> None:
    """Ensure the building exists, the floor/seat (if given) belong to it, and none of them are archived."""
    if building_id is not None:
        building = facility_model.get_building(building_id)
        if not building:
            raise ValidationError("Building not found", field="building_id")
        if building["is_archived"]:
            raise ValidationError("This building is archived", field="building_id")
    if floor_id is not None:
        floor = facility_model.get_floor(floor_id)
        if not floor or floor["building_id"] != building_id:
            raise ValidationError("Floor does not belong to the selected building", field="floor_id")
        if floor["is_archived"]:
            raise ValidationError("This floor is archived", field="floor_id")
    if seat_id is not None:
        seat = facility_model.get_seat(seat_id)
        if not seat or floor_id is None or seat["floor_id"] != floor_id:
            raise ValidationError("Seat does not belong to the selected floor", field="seat_id")
        if seat["is_archived"]:
            raise ValidationError("This seat is archived", field="seat_id")


def _validate_category(category: str) -> str:
    category = (category or "").strip()
    if category not in CATEGORY_KEYS:
        raise ValidationError("Invalid category", field="category")
    return category


def _user_name(user_id: int) -> Optional[str]:
    user = user_model.get_user_by_id(user_id)
    return user["full_name"] if user else None


def create_incident(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new incident reported by the current user."""
    payload = request["body"]
    require_fields(payload, ["title", "category", "building_id"])

    priority = payload.get("priority") or "medium"
    if priority not in VALID_PRIORITIES:
        raise ValidationError("Invalid priority", field="priority")

    building_id = _optional_int(payload["building_id"], "building_id")
    floor_id = _optional_int(payload.get("floor_id"), "floor_id")
    seat_id = _optional_int(payload.get("seat_id"), "seat_id")
    _validate_location(building_id, floor_id, seat_id)

    with transaction():
        incident = incident_model.create_incident(
            title=payload["title"].strip(),
            description=(payload.get("description") or "").strip() or None,
            category=_validate_category(payload["category"]),
            priority=priority,
            building_id=building_id,
            floor_id=floor_id,
            seat_id=seat_id,
            reported_by=request["user"]["id"],
        )
        event_model.create_event(incident["id"], request["user"]["id"], "created", to_value="open")
    return success(incident_model.get_incident(incident["id"]), status=201)


def list_incidents(request: Dict[str, Any]) -> Dict[str, Any]:
    """List incidents, scoped by role and filtered by query parameters."""
    user = request["user"]
    query = request["query"]

    statuses = [status for status in (query.get("status") or "").split(",") if status]
    if any(status not in workflow.STATUSES for status in statuses):
        raise ValidationError("Invalid status filter", field="status")

    filters: Dict[str, Any] = {
        "status": statuses,
        "priority": query.get("priority") or None,
        "category": query.get("category") or None,
        "building_id": _optional_int(query.get("building_id"), "building_id"),
        "assigned_to": _optional_int(query.get("assigned_to"), "assigned_to"),
        "escalated": query.get("escalated") == "true",
        "unassigned": query.get("unassigned") == "true",
        # Archived incidents (location archived) are only listed on request, and only for admins.
        "archived": query.get("archived") == "true" and user["role"] == "facility_admin",
        "search": query.get("search"),
        "sort": query.get("sort") if query.get("sort") in _SORT_OPTIONS else "newest",
    }
    if user["role"] == "employee":
        filters["reported_by"] = user["id"]
    elif user["role"] == "engineer":
        filters["assigned_to"] = user["id"]
        filters["unassigned"] = False
    # facility_admin sees everything, subject to any explicit filters above.

    return success(incident_model.list_incidents(filters))


def get_incident(request: Dict[str, Any], incident_id: str) -> Dict[str, Any]:
    """Retrieve a single incident if the current user is allowed to view it."""
    incident = incident_model.get_incident(int(incident_id))
    if not incident:
        return error("Incident not found", status=404)
    if not can_access_incident(request["user"], incident):
        return error("Insufficient permissions", status=403)
    return success({**incident, "allowed_transitions": _allowed_transitions(request["user"], incident)})


def get_timeline(request: Dict[str, Any], incident_id: str) -> Dict[str, Any]:
    """Return the incident's activity timeline (status changes, assignments, notes, escalations)."""
    incident = incident_model.get_incident(int(incident_id))
    if not incident:
        return error("Incident not found", status=404)
    if not can_access_incident(request["user"], incident):
        return error("Insufficient permissions", status=403)
    return success(event_model.list_events(int(incident_id)))


def _allowed_transitions(user: Dict[str, Any], incident: Dict[str, Any]) -> Any:
    """Archived incidents are read-only, so they offer no status actions."""
    return () if incident["is_archived"] else workflow.allowed_transitions(user["role"], incident["status"])


def _collect_changes(user: Dict[str, Any], incident: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Pick the fields this role may edit from the payload, and validate each of them."""
    editable_fields = {
        "facility_admin": _ADMIN_EDITABLE_FIELDS,
        "engineer": _ENGINEER_EDITABLE_FIELDS,
        "employee": _EMPLOYEE_EDITABLE_FIELDS,
    }[user["role"]]
    changes = {field: payload[field] for field in editable_fields if field in payload}

    if "priority" in changes and changes["priority"] not in VALID_PRIORITIES:
        raise ValidationError("Invalid priority", field="priority")
    if "category" in changes:
        changes["category"] = _validate_category(changes["category"])
    if "title" in changes:
        changes["title"] = str(changes["title"] or "").strip()
        if not changes["title"]:
            raise ValidationError("Title cannot be empty", field="title")

    if "assigned_to" in changes:
        changes["assigned_to"] = _optional_int(changes["assigned_to"], "assigned_to")
        if changes["assigned_to"] is not None and not engineer_model.get_profile(changes["assigned_to"]):
            raise ValidationError("Incidents can only be assigned to engineers", field="assigned_to")

    if any(field in changes for field in ("building_id", "floor_id", "seat_id")):
        location = {
            field: _optional_int(changes.get(field, incident.get(field)), field)
            for field in ("building_id", "floor_id", "seat_id")
        }
        _validate_location(location["building_id"], location["floor_id"], location["seat_id"])
        changes.update({field: location[field] for field in location if field in changes})

    if "is_escalated" in changes:
        changes["is_escalated"] = bool(changes["is_escalated"])
        reason = str(changes.get("escalation_reason") or "").strip()
        if changes["is_escalated"] and not incident["is_escalated"] and not reason:
            raise ValidationError("Please explain why this incident needs escalation", field="escalation_reason")
        if not changes["is_escalated"]:
            changes["escalation_reason"] = None

    if changes.get("status") == incident["status"]:
        del changes["status"]
    return changes


def update_incident(request: Dict[str, Any], incident_id: str) -> Dict[str, Any]:
    """Update incident fields the current user's role is allowed to change.

    Status changes follow the role's workflow transitions. Blocking, resolving and reopening require a
    `status_reason`, which is also posted to the notes thread so the reporter is kept informed.
    """
    incident = incident_model.get_incident(int(incident_id))
    if not incident:
        return error("Incident not found", status=404)

    user = request["user"]
    if not can_access_incident(user, incident):
        return error("Insufficient permissions", status=403)
    if incident["is_archived"]:
        return error("This incident is archived because its location was archived. Restore the location to edit it.", status=409)

    payload = request["body"]
    changes = _collect_changes(user, incident, payload)

    reason = str(payload.get("status_reason") or "").strip()
    new_status = changes.get("status")
    if new_status:
        workflow.validate_transition(user["role"], incident["status"], new_status)
        if workflow.requires_reason(incident["status"], new_status) and not reason:
            raise ValidationError("Please add a short explanation for this status change", field="status_reason")
        if new_status == "blocked":
            changes["blocked_reason"] = reason
        elif incident["status"] == "blocked":
            changes["blocked_reason"] = None

    if not changes:
        raise ValidationError("No permitted fields to update")

    with transaction():
        incident_model.update_incident(int(incident_id), changes)
        incident_model.apply_milestones(int(incident_id), workflow.milestone_updates(incident, changes, user["role"]))
        for event in workflow.change_events(incident, changes, reason if new_status else None, _user_name):
            event_model.create_event(int(incident_id), user["id"], **event)
        if new_status and reason:
            note_model.create_note(
                int(incident_id), user["id"], workflow.status_note(incident["status"], new_status, reason)
            )

    updated = incident_model.get_incident(int(incident_id))
    return success({**updated, "allowed_transitions": _allowed_transitions(user, updated)})


def delete_incident(request: Dict[str, Any], incident_id: str) -> Dict[str, Any]:
    """Delete an incident (route restricts this to facility admins)."""
    if not incident_model.delete_incident(int(incident_id)):
        return error("Incident not found", status=404)
    return no_content()
