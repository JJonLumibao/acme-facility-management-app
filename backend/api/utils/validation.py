"""Simple request payload validation helpers."""
from typing import Any, Dict, Iterable, Optional


class ValidationError(Exception):
    """Raised when a request payload fails validation."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


def require_fields(payload: Dict[str, Any], fields: Iterable[str]) -> None:
    """Raise a ValidationError if any of the given fields are missing or empty."""
    missing = [field for field in fields if not str(payload.get(field, "")).strip()]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")
