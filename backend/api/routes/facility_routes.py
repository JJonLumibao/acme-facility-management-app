"""Route registrations for buildings, floors, and seats."""
from auth.middleware import require_roles
from controllers import facility_controller
from routes.router import Router


def register(router: Router) -> None:
    """Register facility (building/floor/seat) routes on the given router."""
    router.post("/buildings", require_roles("facility_admin")(facility_controller.create_building))
    router.get("/buildings", require_roles()(facility_controller.list_buildings))
    router.get("/buildings/{building_id}", require_roles()(facility_controller.get_building))
    router.put("/buildings/{building_id}", require_roles("facility_admin")(facility_controller.update_building))
    router.delete("/buildings/{building_id}", require_roles("facility_admin")(facility_controller.delete_building))

    router.post(
        "/buildings/{building_id}/floors", require_roles("facility_admin")(facility_controller.create_floor)
    )
    router.get("/buildings/{building_id}/floors", require_roles()(facility_controller.list_floors))
    router.get("/floors/{floor_id}", require_roles()(facility_controller.get_floor))
    router.put("/floors/{floor_id}", require_roles("facility_admin")(facility_controller.update_floor))
    router.delete("/floors/{floor_id}", require_roles("facility_admin")(facility_controller.delete_floor))

    router.post("/floors/{floor_id}/seats", require_roles("facility_admin")(facility_controller.create_seat))
    router.get("/floors/{floor_id}/seats", require_roles()(facility_controller.list_seats))
    router.get("/seats/{seat_id}", require_roles()(facility_controller.get_seat))
    router.put("/seats/{seat_id}", require_roles("facility_admin")(facility_controller.update_seat))
    router.delete("/seats/{seat_id}", require_roles("facility_admin")(facility_controller.delete_seat))
