"""Route registrations for engineer profile management."""
from auth.middleware import require_roles
from controllers import engineer_controller
from routes.router import Router


def register(router: Router) -> None:
    """Register engineer profile routes on the given router."""
    router.post("/engineers", require_roles("facility_admin")(engineer_controller.create_engineer))
    router.get("/engineers", require_roles("facility_admin")(engineer_controller.list_engineers))
    # Must be registered before /engineers/{engineer_id}, which would otherwise match "workload".
    router.get("/engineers/workload", require_roles("facility_admin")(engineer_controller.get_workload))
    router.get("/engineers/{engineer_id}", require_roles()(engineer_controller.get_engineer))
    router.put(
        "/engineers/{engineer_id}",
        require_roles("facility_admin", "engineer")(engineer_controller.update_engineer),
    )
    router.delete("/engineers/{engineer_id}", require_roles("facility_admin")(engineer_controller.delete_engineer))
