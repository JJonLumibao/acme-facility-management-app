"""Business logic for buildings, floors, and seats."""
from typing import Any, Callable, Dict, Optional

from db import transaction
from models import facility_model
from utils.responses import error, no_content, success
from utils.validation import ValidationError, require_fields


def _include_archived(request: Dict[str, Any]) -> bool:
    """Archived locations are hidden unless ?include_archived=true (used by the admin Facilities page)."""
    return request["query"].get("include_archived") == "true"


def _ensure_parent_active(kind: str, record: Dict[str, Any]) -> None:
    """A floor/seat can't be restored while the building/floor it belongs to is still archived."""
    if kind == "floor":
        parent: Optional[Dict[str, Any]] = facility_model.get_building(record["building_id"])
        parent_kind = "building"
    elif kind == "seat":
        parent = facility_model.get_floor(record["floor_id"])
        parent_kind = "floor"
    else:
        return
    if parent and parent["is_archived"]:
        raise ValidationError(f"Restore the {parent_kind} first", field="is_archived")


def _save(
    kind: str,
    record_id: int,
    request: Dict[str, Any],
    update: Callable[[int, Dict[str, Any]], Optional[Dict[str, Any]]],
    get: Callable[[int], Optional[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Apply field edits and, if `is_archived` changes, cascade the archive/restore - all in one transaction."""
    changes = dict(request["body"])
    is_archived = changes.pop("is_archived", None)
    if is_archived is not None and not isinstance(is_archived, bool):
        raise ValidationError("is_archived must be true or false", field="is_archived")

    with transaction():
        record = update(record_id, changes)
        if not record:
            return error(f"{kind.capitalize()} not found", status=404)
        if is_archived is not None and is_archived != record["is_archived"]:
            if not is_archived:
                _ensure_parent_active(kind, record)
            facility_model.set_archived(kind, record_id, is_archived)
            record = get(record_id)
    return success(record)


def create_building(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new building."""
    payload = request["body"]
    require_fields(payload, ["name"])
    building = facility_model.create_building(payload["name"].strip(), payload.get("address"))
    return success(building, status=201)


def list_buildings(request: Dict[str, Any]) -> Dict[str, Any]:
    """List all buildings."""
    return success(facility_model.list_buildings(_include_archived(request)))


def get_building(request: Dict[str, Any], building_id: str) -> Dict[str, Any]:
    """Retrieve a single building by id."""
    building = facility_model.get_building(int(building_id))
    if not building:
        return error("Building not found", status=404)
    return success(building)


def update_building(request: Dict[str, Any], building_id: str) -> Dict[str, Any]:
    """Update a building's name/address, or archive/restore it with its floors, seats and incidents."""
    return _save("building", int(building_id), request, facility_model.update_building, facility_model.get_building)


def delete_building(request: Dict[str, Any], building_id: str) -> Dict[str, Any]:
    """Delete a building."""
    if not facility_model.delete_building(int(building_id)):
        return error("Building not found", status=404)
    return no_content()


def create_floor(request: Dict[str, Any], building_id: str) -> Dict[str, Any]:
    """Create a floor under a building."""
    payload = request["body"]
    require_fields(payload, ["name"])
    floor = facility_model.create_floor(int(building_id), payload["name"].strip())
    return success(floor, status=201)


def list_floors(request: Dict[str, Any], building_id: str) -> Dict[str, Any]:
    """List floors within a building."""
    return success(facility_model.list_floors(int(building_id), _include_archived(request)))


def get_floor(request: Dict[str, Any], floor_id: str) -> Dict[str, Any]:
    """Retrieve a single floor by id."""
    floor = facility_model.get_floor(int(floor_id))
    if not floor:
        return error("Floor not found", status=404)
    return success(floor)


def update_floor(request: Dict[str, Any], floor_id: str) -> Dict[str, Any]:
    """Update a floor's name, or archive/restore it with its seats and incidents."""
    return _save("floor", int(floor_id), request, facility_model.update_floor, facility_model.get_floor)


def delete_floor(request: Dict[str, Any], floor_id: str) -> Dict[str, Any]:
    """Delete a floor."""
    if not facility_model.delete_floor(int(floor_id)):
        return error("Floor not found", status=404)
    return no_content()


def create_seat(request: Dict[str, Any], floor_id: str) -> Dict[str, Any]:
    """Create a seat under a floor."""
    payload = request["body"]
    require_fields(payload, ["label"])
    seat = facility_model.create_seat(int(floor_id), payload["label"].strip())
    return success(seat, status=201)


def list_seats(request: Dict[str, Any], floor_id: str) -> Dict[str, Any]:
    """List seats within a floor."""
    return success(facility_model.list_seats(int(floor_id), _include_archived(request)))


def get_seat(request: Dict[str, Any], seat_id: str) -> Dict[str, Any]:
    """Retrieve a single seat by id."""
    seat = facility_model.get_seat(int(seat_id))
    if not seat:
        return error("Seat not found", status=404)
    return success(seat)


def update_seat(request: Dict[str, Any], seat_id: str) -> Dict[str, Any]:
    """Update a seat's label, or archive/restore it with its incidents."""
    return _save("seat", int(seat_id), request, facility_model.update_seat, facility_model.get_seat)


def delete_seat(request: Dict[str, Any], seat_id: str) -> Dict[str, Any]:
    """Delete a seat."""
    if not facility_model.delete_seat(int(seat_id)):
        return error("Seat not found", status=404)
    return no_content()
