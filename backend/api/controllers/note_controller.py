"""Business logic for incident notes."""
from typing import Any, Dict

from db import transaction
from models import event_model, incident_model, note_model
from utils.permissions import can_access_incident
from utils.responses import error, no_content, success
from utils.validation import require_fields
from utils.workflow import STAFF_ROLES


def create_note(request: Dict[str, Any], incident_id: str) -> Dict[str, Any]:
    """Add a note to an incident the current user has access to (closed incidents are read-only)."""
    incident = incident_model.get_incident(int(incident_id))
    if not incident:
        return error("Incident not found", status=404)
    user = request["user"]
    if not can_access_incident(user, incident):
        return error("Insufficient permissions", status=403)
    if incident["is_archived"]:
        return error("This incident is archived and read-only.", status=409)
    if incident["status"] == "closed" and user["role"] != "facility_admin":
        return error("This incident is closed. Ask a facility admin to reopen it.", status=409)

    payload = request["body"]
    require_fields(payload, ["message"])
    with transaction():
        note = note_model.create_note(int(incident_id), user["id"], payload["message"].strip())
        event_model.create_event(int(incident_id), user["id"], "note_added")
        if user["role"] in STAFF_ROLES:
            # A staff reply is the first sign to the reporter that someone is looking at the ticket.
            incident_model.apply_milestones(int(incident_id), {"acknowledged_at": "set_if_null"})
    return success(note, status=201)


def list_notes(request: Dict[str, Any], incident_id: str) -> Dict[str, Any]:
    """List notes for an incident the current user has access to."""
    incident = incident_model.get_incident(int(incident_id))
    if not incident:
        return error("Incident not found", status=404)
    if not can_access_incident(request["user"], incident):
        return error("Insufficient permissions", status=403)
    return success(note_model.list_notes(int(incident_id)))


def delete_note(request: Dict[str, Any], note_id: str) -> Dict[str, Any]:
    """Delete a note (author or facility admin only)."""
    note = note_model.get_note(int(note_id))
    if not note:
        return error("Note not found", status=404)
    user = request["user"]
    if user["role"] != "facility_admin" and note["author_id"] != user["id"]:
        return error("Insufficient permissions", status=403)
    note_model.delete_note(int(note_id))
    return no_content()
