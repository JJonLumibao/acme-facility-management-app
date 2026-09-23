"""Route registrations for incident tickets."""
from auth.middleware import require_roles
from controllers import incident_controller
from routes.router import Router


def register(router: Router) -> None:
    """Register incident routes on the given router."""
    router.post("/incidents", require_roles()(incident_controller.create_incident))
    router.get("/incidents", require_roles()(incident_controller.list_incidents))
    router.get("/incidents/{incident_id}", require_roles()(incident_controller.get_incident))
    router.put("/incidents/{incident_id}", require_roles()(incident_controller.update_incident))
    router.get("/incidents/{incident_id}/timeline", require_roles()(incident_controller.get_timeline))
    router.delete("/incidents/{incident_id}", require_roles("facility_admin")(incident_controller.delete_incident))
