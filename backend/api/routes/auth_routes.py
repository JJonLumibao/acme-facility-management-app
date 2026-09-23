"""Route registrations for authentication endpoints."""
from controllers import auth_controller
from routes.router import Router


def register(router: Router) -> None:
    """Register auth routes on the given router."""
    router.post("/auth/register", auth_controller.register)
    router.post("/auth/login", auth_controller.login)
    router.post("/auth/refresh", auth_controller.refresh)
