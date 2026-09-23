"""Application entry point: builds the router and dispatches Lambda events to route handlers."""
import logging
import os
from typing import Any, Dict, Optional

from psycopg import errors as pg_errors

from auth.middleware import AuthError
from db import init_schema
from routes import (
    assistant_routes,
    auth_routes,
    catalog_routes,
    dashboard_routes,
    engineer_routes,
    facility_routes,
    incident_routes,
    note_routes,
    user_routes,
)
from routes.router import Router
from utils.request import parse_event
from utils.responses import error, success
from utils.validation import ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

router = Router()
router.get("/", lambda request: success({"status": "ok"}))
auth_routes.register(router)
user_routes.register(router)
catalog_routes.register(router)
engineer_routes.register(router)
facility_routes.register(router)
incident_routes.register(router)
note_routes.register(router)
dashboard_routes.register(router)
assistant_routes.register(router)


_DEMO_DATA_CHECKED = False


def _seed_demo_data_once() -> None:
    """If SEED_DEMO_DATA=true (set by Terraform in the cloud only), load demo data into an empty database.

    Checked once per Lambda instance; seed.seed_if_empty() never runs once buildings or incidents exist.
    """
    global _DEMO_DATA_CHECKED
    if _DEMO_DATA_CHECKED:
        return
    if os.getenv("SEED_DEMO_DATA") == "true":
        from seed import seed_if_empty  # imported lazily: only needed when the feature is on

        if seed_if_empty():
            logger.info("Database was empty: loaded demo data")
    _DEMO_DATA_CHECKED = True  # only after success, so a failed attempt is retried on the next request


def handler(event: Optional[Dict[str, Any]] = None, context: Any = None) -> Dict[str, Any]:
    """AWS Lambda entry point for the facility incident management API."""
    logger.debug("Received event: %s", event)
    request = parse_event(event or {})

    try:
        init_schema()
        _seed_demo_data_once()
        route_handler, path_params = router.match(request["method"], request["path"])
        if route_handler is None:
            return error("Not found", status=404)
        return route_handler(request, **path_params)
    except ValidationError as exc:
        return error(exc.message, status=400, details={"field": exc.field} if exc.field else None)
    except AuthError as exc:
        return error(exc.message, status=exc.status)
    except pg_errors.ForeignKeyViolation:
        # e.g. deleting a building/seat that incidents still point to, or a user with ticket history.
        return error("This record is still referenced by incidents or notes and cannot be deleted.", status=409)
    except Exception as exc:  # noqa: BLE001 - top-level safety net for Lambda invocation
        logger.error("Unhandled error: %s", str(exc))
        return error("Internal server error", status=500)


if __name__ == "__main__":
    print(handler({"rawPath": "/", "requestContext": {"http": {"method": "GET"}}}))
