"""Route registrations for admin-only operator actions."""
from auth.middleware import require_roles
from controllers import admin_controller
from routes.router import Router


def register(router: Router) -> None:
    """Register admin routes on the given router."""
    router.post("/admin/reset-demo-data", require_roles("facility_admin")(admin_controller.reset_demo_data))
