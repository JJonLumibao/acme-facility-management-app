"""Operator actions for facility admins (demo environments only)."""
import logging
from typing import Any, Dict

import seed
from utils.responses import error, success
from utils.validation import ValidationError

logger = logging.getLogger(__name__)

CONFIRMATION = "RESET"


def reset_demo_data(request: Dict[str, Any]) -> Dict[str, Any]:
    """Delete all data and restore the demo data set. Admin-only; requires {"confirm": "RESET"}."""
    if not seed.demo_reset_enabled():
        return error("Not available", status=404)
    if request["body"].get("confirm") != CONFIRMATION:
        raise ValidationError(f'Send {{"confirm": "{CONFIRMATION}"}} to reset the demo data', field="confirm")

    seed.reset_and_seed(verbose=False)
    logger.warning("Demo data reset by admin user %s", request["user"]["id"])
    return success({"reset": True, "users": len(seed.USERS), "incidents": len(seed.INCIDENTS)})
