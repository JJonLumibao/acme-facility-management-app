"""Business logic for managing engineer profiles (facility admin only, except self-view/update)."""
from typing import Any, Dict, Optional

from auth.security import hash_password
from controllers.auth_controller import ALLOWED_EMAIL_DOMAIN
from db import transaction
from models import engineer_model, user_model
from utils import workload
from utils.catalog import DEPARTMENT_KEYS, department_for_category
from utils.responses import error, no_content, success
from utils.validation import ValidationError, require_fields

# Engineers may only toggle their own availability; everything else is managed by facility admins.
_ENGINEER_SELF_EDITABLE = ("is_available",)


def _validate_department(department: Optional[str]) -> Optional[str]:
    if department in (None, ""):
        return None
    if department not in DEPARTMENT_KEYS:
        raise ValidationError("Invalid department", field="department")
    return department


def create_engineer(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new engineer user account plus its profile."""
    payload = request["body"]
    require_fields(payload, ["email", "password", "full_name"])

    email = payload["email"].strip().lower()
    if not email.endswith(f"@{ALLOWED_EMAIL_DOMAIN}"):
        raise ValidationError(f"Email must be a @{ALLOWED_EMAIL_DOMAIN} address", field="email")
    if user_model.get_user_by_email(email):
        raise ValidationError("Email is already registered", field="email")

    department = _validate_department(payload.get("department"))
    password_hash = hash_password(payload["password"])
    with transaction():
        user = user_model.create_user(email, password_hash, payload["full_name"].strip(), "engineer")
        engineer_model.create_profile(
            user["id"], payload.get("title"), payload.get("skills"), department, payload.get("is_available", True)
        )
    return success(engineer_model.get_profile(user["id"]), status=201)


def list_engineers(request: Dict[str, Any]) -> Dict[str, Any]:
    """List all engineer profiles."""
    return success(engineer_model.list_profiles())


def get_workload(request: Dict[str, Any]) -> Dict[str, Any]:
    """Engineer workload with load levels; pass ?category= to rank engineers for assigning that category."""
    department = department_for_category(request["query"].get("category"))
    return success({
        "department": department,
        "thresholds": {"moderate": workload.MODERATE_THRESHOLD, "heavy": workload.HEAVY_THRESHOLD},
        "engineers": workload.rank_for_assignment(engineer_model.list_workload(), department),
    })


def get_engineer(request: Dict[str, Any], engineer_id: str) -> Dict[str, Any]:
    """Retrieve a single engineer profile by user id."""
    current = request["user"]
    if current["role"] == "engineer" and current["id"] != int(engineer_id):
        return error("Insufficient permissions", status=403)
    profile = engineer_model.get_profile(int(engineer_id))
    if not profile:
        return error("Engineer not found", status=404)
    return success(profile)


def update_engineer(request: Dict[str, Any], engineer_id: str) -> Dict[str, Any]:
    """Update an engineer profile (admins: everything; engineers: their own availability only)."""
    current = request["user"]
    changes = dict(request["body"])
    if current["role"] == "engineer":
        if current["id"] != int(engineer_id):
            return error("Insufficient permissions", status=403)
        changes = {field: changes[field] for field in _ENGINEER_SELF_EDITABLE if field in changes}
    if "department" in changes:
        changes["department"] = _validate_department(changes["department"])
    if "is_available" in changes:
        changes["is_available"] = bool(changes["is_available"])

    profile = engineer_model.update_profile(int(engineer_id), changes)
    if not profile:
        return error("Engineer not found", status=404)
    return success(profile)


def delete_engineer(request: Dict[str, Any], engineer_id: str) -> Dict[str, Any]:
    """Delete an engineer's user account and profile."""
    if not engineer_model.get_profile(int(engineer_id)):
        return error("Engineer not found", status=404)
    user_model.delete_user(int(engineer_id))
    return no_content()
