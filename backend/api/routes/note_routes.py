"""Route registrations for incident notes."""
from auth.middleware import require_roles
from controllers import note_controller
from routes.router import Router


def register(router: Router) -> None:
    """Register incident note routes on the given router."""
    router.post("/incidents/{incident_id}/notes", require_roles()(note_controller.create_note))
    router.get("/incidents/{incident_id}/notes", require_roles()(note_controller.list_notes))
    router.delete("/notes/{note_id}", require_roles()(note_controller.delete_note))
