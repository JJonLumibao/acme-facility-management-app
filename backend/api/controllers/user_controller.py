"""Business logic for the authenticated user's own profile."""
from typing import Any, Dict

from models import user_model
from utils.responses import success


def get_me(request: Dict[str, Any]) -> Dict[str, Any]:
    """Return the profile of the currently authenticated user."""
    user = user_model.get_user_by_id(request["user"]["id"])
    return success(user)
