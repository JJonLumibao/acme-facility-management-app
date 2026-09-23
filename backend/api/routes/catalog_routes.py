"""Route registrations for reference data (categories, departments, workflow)."""
from auth.middleware import require_roles
from controllers import catalog_controller
from routes.router import Router


def register(router: Router) -> None:
    """Register catalog routes on the given router."""
    router.get("/catalog", require_roles()(catalog_controller.get_catalog))
