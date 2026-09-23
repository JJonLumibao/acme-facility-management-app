"""Route registrations for the in-app assistant."""
from auth.middleware import require_roles
from controllers import assistant_controller
from routes.router import Router


def register(router: Router) -> None:
    """Register assistant routes on the given router (any signed-in user; answers are role-scoped)."""
    router.get("/assistant", require_roles()(assistant_controller.get_suggestions))
    router.post("/assistant", require_roles()(assistant_controller.ask))
