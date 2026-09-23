"""Business logic for the in-app assistant (POST /assistant, GET /assistant)."""
import logging
import time
from typing import Any, Dict

from assistant import builtin
from utils.responses import success
from utils.validation import ValidationError

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 500


def ask(request: Dict[str, Any]) -> Dict[str, Any]:
    """Answer a question from the role-scoped reporting tools."""
    message = str(request["body"].get("message") or "").strip()
    if not message:
        raise ValidationError("Please type a question", field="message")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValidationError(f"Questions are limited to {MAX_MESSAGE_LENGTH} characters", field="message")

    started = time.monotonic()
    response = builtin.answer(message, request["user"])
    # Never log the question itself; only how long answering took.
    logger.info("Assistant answered in %dms", (time.monotonic() - started) * 1000)
    return success(response)


def get_suggestions(request: Dict[str, Any]) -> Dict[str, Any]:
    """Starter questions for the user's role (shown when the assistant opens)."""
    return success({"suggestions": builtin.suggestions_for(request["user"])})
