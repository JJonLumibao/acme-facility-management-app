"""Route registrations for dashboard summary endpoints."""
from auth.middleware import require_roles
from controllers import dashboard_controller
from routes.router import Router


def register(router: Router) -> None:
    """Register dashboard routes on the given router."""
    router.get("/dashboard/summary", require_roles()(dashboard_controller.get_summary))
