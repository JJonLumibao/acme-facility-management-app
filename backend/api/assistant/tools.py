"""The assistant's tools: the only data it can see.

Each tool wraps an existing reporting function and applies the caller's role scope (the same one the
dashboard uses), so the assistant can never reveal more than the user could already see. Used today by the
built-in assistant; the descriptions and input schemas are written so an LLM could call the same tools
later (via tool_specs/run_tool) without ever writing SQL.
"""
from typing import Any, Callable, Dict, List, Optional

from models import dashboard_model, engineer_model, incident_model
from utils import workflow, workload
from utils.catalog import CATEGORIES, CATEGORY_KEYS, DEPARTMENTS, department_for_category
from utils.permissions import report_scope

ADMIN = "facility_admin"
ADMIN_ONLY_MESSAGE = "This information is only available to facility admins."

_CATEGORY_LABELS = {category["key"]: category["label"] for category in CATEGORIES}
_DEPARTMENT_LABELS = {department["key"]: department["label"] for department in DEPARTMENTS}
_PRIORITIES = ("low", "medium", "high", "critical")


class ToolInputError(ValueError):
    """Raised when a caller passes arguments a tool doesn't accept."""


def category_label(key: Optional[str]) -> str:
    return _CATEGORY_LABELS.get(key or "", (key or "unknown").replace("_", " "))


def department_label(key: Optional[str]) -> str:
    return _DEPARTMENT_LABELS.get(key or "", "No department")


def _location(*parts: Optional[str]) -> str:
    return " · ".join(part for part in parts if part) or "No location"


# --- Tool implementations -------------------------------------------------------------------------

def get_overview(user: Dict[str, Any]) -> Dict[str, Any]:
    scope = report_scope(user)
    return {"counts": dashboard_model.kpis(scope), "by_status": dashboard_model.count_by("status", scope)}


def get_hotspots(user: Dict[str, Any]) -> Dict[str, Any]:
    spots = dashboard_model.hotspots()
    return {
        "buildings": spots["buildings"],
        "floors": spots["floors"],
        "seats": spots["seats"],
        "recurring": [
            {
                "category": category_label(row["category"]),
                "location": _location(row["building_name"], row["floor_name"], row["seat_label"]),
                "count": row["count"],
                "last_reported_at": row["last_reported_at"],
            }
            for row in spots["recurring"]
        ],
    }


def get_response_times(user: Dict[str, Any]) -> Dict[str, Any]:
    return {"hours_from_report": dashboard_model.response_times(report_scope(user))}


def get_attention_items(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "items": [
            {
                "id": item["id"], "title": item["title"], "status": item["status"], "priority": item["priority"],
                "escalated": item["is_escalated"], "escalation_reason": item["escalation_reason"],
                "blocked_reason": item["blocked_reason"], "assignee": item["assignee_name"],
                "building": item["building_name"],
            }
            for item in dashboard_model.needs_attention(report_scope(user))
        ]
    }


def get_top_categories(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "categories": [
            {
                "category": category_label(row["category"]),
                "department": department_label(department_for_category(row["category"])),
                "total": row["count"],
                "active": row["active"],
            }
            for row in dashboard_model.by_category(report_scope(user))
        ]
    }


def get_engineer_workload(user: Dict[str, Any]) -> Dict[str, Any]:
    engineers = workload.rank_for_assignment(engineer_model.list_workload(), None)
    return {
        "thresholds": {"moderate": workload.MODERATE_THRESHOLD, "heavy": workload.HEAVY_THRESHOLD},
        "engineers": [
            {
                "name": engineer["full_name"], "department": department_label(engineer["department"]),
                "available": engineer["is_available"], "active": engineer["active_count"],
                "urgent": engineer["urgent_count"], "blocked": engineer["blocked_count"],
                "load_level": engineer["load_level"], "resolved_last_30_days": engineer["resolved_30d"],
                "avg_resolve_hours": engineer["avg_resolve_hours"],
            }
            for engineer in sorted(engineers, key=lambda e: -e["load_score"])
        ],
    }


def get_communication_stats(user: Dict[str, Any]) -> Dict[str, Any]:
    return dashboard_model.communication(report_scope(user))


def find_incidents(
    user: Dict[str, Any],
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    escalated: Optional[bool] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    filters: Dict[str, Any] = {**report_scope(user), "sort": "priority"}
    if status == "active":
        filters["status"] = list(workflow.ACTIVE_STATUSES)
    elif status:
        filters["status"] = [status]
    if category:
        filters["category"] = category
    if priority:
        filters["priority"] = priority
    if escalated:
        filters["escalated"] = True
    if search:
        filters["search"] = search
    incidents = incident_model.list_incidents(filters)
    return {
        "total_matching": len(incidents),
        "incidents": [
            {
                "id": row["id"], "title": row["title"], "status": row["status"], "priority": row["priority"],
                "category": category_label(row["category"]),
                "location": _location(row["building_name"], row["floor_name"], row["seat_label"]),
                "assignee": row["assignee_name"], "reported_at": row["created_at"],
                "escalated": row["is_escalated"], "blocked_reason": row["blocked_reason"],
            }
            for row in incidents[:10]
        ],
    }


# --- Registry -------------------------------------------------------------------------------------

_NO_ARGS: Dict[str, Any] = {"type": "object", "properties": {}, "additionalProperties": False}

_TOOLS: Dict[str, Dict[str, Any]] = {
    "get_overview": {
        "fn": get_overview, "admin_only": False, "link": {"label": "View active incidents", "to": "/incidents?view=active"},
        "description": "Counts of incidents in the user's scope: active, unassigned, escalated, blocked, resolved in the "
                       "last 7 days, total, and a breakdown by status. Use for 'what is open', 'how many', 'status'.",
        "input_schema": _NO_ARGS,
    },
    "get_hotspots": {
        "fn": get_hotspots, "admin_only": True, "link": None,
        "description": "Top buildings, floors and seats by number of incidents (with how many are still active), plus "
                       "recurring issues: the same category reported at the same location 2+ times.",
        "input_schema": _NO_ARGS,
    },
    "get_response_times": {
        "fn": get_response_times, "admin_only": False, "link": None,
        "description": "Median and average hours from report to acknowledged, assigned, work started and resolved, "
                       "with how many incidents each figure is based on.",
        "input_schema": _NO_ARGS,
    },
    "get_attention_items": {
        "fn": get_attention_items, "admin_only": False,
        "link": {"label": "View escalated incidents", "to": "/incidents?view=escalated"},
        "description": "Active incidents that are escalated or blocked, with the escalation/blocked reason, assignee "
                       "and building, most urgent first.",
        "input_schema": _NO_ARGS,
    },
    "get_top_categories": {
        "fn": get_top_categories, "admin_only": False, "link": None,
        "description": "Incident counts per issue category (total and still active) with the responsible department, "
                       "most common first.",
        "input_schema": _NO_ARGS,
    },
    "get_engineer_workload": {
        "fn": get_engineer_workload, "admin_only": True, "link": {"label": "Open workload tracker", "to": "/engineers"},
        "description": "Each engineer's department, availability, active/urgent/blocked ticket counts, load level "
                       "(light/moderate/heavy), tickets resolved in 30 days and average resolve time.",
        "input_schema": _NO_ARGS,
    },
    "get_communication_stats": {
        "fn": get_communication_stats, "admin_only": True, "link": None,
        "description": "How well reporters are kept informed: share of tickets with a staff update, average time to "
                       "first staff reply, resolved tickets with an explanation, active tickets with no recent "
                       "update, and reopened tickets.",
        "input_schema": _NO_ARGS,
    },
    "find_incidents": {
        "fn": find_incidents, "admin_only": False, "link": {"label": "Open incidents list", "to": "/incidents"},
        "description": "Look up individual incidents in the user's scope (max 10, most urgent first). All filters "
                       "are optional.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", *workflow.STATUSES],
                           "description": "'active' means open, in progress or blocked."},
                "category": {"type": "string", "enum": sorted(CATEGORY_KEYS)},
                "priority": {"type": "string", "enum": list(_PRIORITIES)},
                "escalated": {"type": "boolean"},
                "search": {"type": "string", "description": "Text in the title/description, or '#<id>'."},
            },
            "additionalProperties": False,
        },
    },
}


def tool_specs(user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Tool definitions (LLM tool-use format), limited to what this user's role may use (stable order)."""
    return [
        {"name": name, "description": tool["description"], "input_schema": tool["input_schema"]}
        for name, tool in _TOOLS.items()
        if user["role"] == ADMIN or not tool["admin_only"]
    ]


def tool_link(name: str) -> Optional[Dict[str, str]]:
    """Deep link into the app that shows more detail for a tool's topic."""
    tool = _TOOLS.get(name)
    return tool["link"] if tool else None


def _validate_args(name: str, args: Any) -> Dict[str, Any]:
    """Check model-supplied arguments against the tool's schema (types, enums, no extra keys)."""
    if args in (None, ""):
        args = {}
    if not isinstance(args, dict):
        raise ToolInputError("Arguments must be an object")
    properties = _TOOLS[name]["input_schema"]["properties"]
    unknown = set(args) - set(properties)
    if unknown:
        raise ToolInputError(f"Unknown argument(s): {', '.join(sorted(unknown))}")
    clean: Dict[str, Any] = {}
    for key, value in args.items():
        if value is None:
            continue
        spec = properties[key]
        if spec["type"] == "boolean":
            if not isinstance(value, bool):
                raise ToolInputError(f"{key} must be true or false")
        elif not isinstance(value, str) or len(value) > 100:
            raise ToolInputError(f"{key} must be a short string")
        elif "enum" in spec and value not in spec["enum"]:
            raise ToolInputError(f"{key} must be one of: {', '.join(spec['enum'])}")
        clean[key] = value
    return clean


def run_tool(name: str, args: Any, user: Dict[str, Any]) -> Dict[str, Any]:
    """Run a tool for this user. Returns the data, or {'error': ...} for unknown/forbidden/invalid calls."""
    tool = _TOOLS.get(name)
    if tool is None:
        return {"error": f"Unknown tool: {name}"}
    if tool["admin_only"] and user["role"] != ADMIN:
        return {"error": ADMIN_ONLY_MESSAGE}
    try:
        clean_args = _validate_args(name, args)
    except ToolInputError as exc:
        return {"error": str(exc)}
    fn: Callable[..., Dict[str, Any]] = tool["fn"]
    return fn(user, **clean_args)


def is_admin_only(name: str) -> bool:
    return bool(_TOOLS.get(name, {}).get("admin_only"))
