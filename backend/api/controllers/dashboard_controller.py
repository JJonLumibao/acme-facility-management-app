"""Business logic for role-scoped incident dashboards."""
from typing import Any, Dict

from models import dashboard_model
from utils.responses import success


def get_summary(request: Dict[str, Any]) -> Dict[str, Any]:
    """Return dashboard metrics scoped by the caller's role.

    Employees see their reported tickets, engineers their assigned tickets, facility admins everything.
    Organisation-wide sections (hotspots, assignee distribution, communication) are admin-only.
    """
    user = request["user"]
    scope: Dict[str, Any] = {}
    if user["role"] == "employee":
        scope["reported_by"] = user["id"]
    elif user["role"] == "engineer":
        scope["assigned_to"] = user["id"]
    is_admin = user["role"] == "facility_admin"

    return success({
        "kpis": dashboard_model.kpis(scope),
        "by_status": dashboard_model.count_by("status", scope),
        "by_priority": dashboard_model.count_by("priority", scope),
        "by_category": dashboard_model.by_category(scope),
        "response_times": dashboard_model.response_times(scope),
        "needs_attention": dashboard_model.needs_attention(scope),
        "by_assignee": dashboard_model.by_assignee() if is_admin else None,
        "hotspots": dashboard_model.hotspots() if is_admin else None,
        "communication": dashboard_model.communication(scope) if is_admin else None,
    })
