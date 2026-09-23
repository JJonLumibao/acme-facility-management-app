"""Route registrations for the authenticated user's own profile."""
from auth.middleware import require_roles
from controllers import user_controller
from routes.router import Router


def register(router: Router) -> None:
    """Register user profile routes on the given router."""
    router.get("/users/me", require_roles()(user_controller.get_me))
