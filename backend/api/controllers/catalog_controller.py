"""Reference data the frontend needs to render forms and workflow actions consistently with the API."""
from typing import Any, Dict

from utils import workflow
from utils.catalog import CATEGORIES, DEPARTMENTS
from utils.responses import success


def get_catalog(request: Dict[str, Any]) -> Dict[str, Any]:
    """Return categories, departments, statuses and the caller's allowed status transitions."""
    return success({
        "categories": CATEGORIES,
        "departments": DEPARTMENTS,
        "statuses": [{"key": key, "label": workflow.STATUS_LABELS[key]} for key in workflow.STATUSES],
        "transitions": workflow.TRANSITIONS_BY_ROLE.get(request["user"]["role"], {}),
    })
