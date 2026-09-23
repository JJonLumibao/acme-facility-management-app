"""Local-only dev server: wraps the Lambda handler with FastAPI/uvicorn for quick curl/Postman testing.

Not deployed to AWS. Terraform only packages requirements.txt (see requirements-dev.txt for these deps).

Run with:
    pip install -r requirements.txt -r requirements-dev.txt
    IS_LOCAL=true POSTGRES_USER=postgres POSTGRES_PASS=postgres123 POSTGRES_NAME=postgres \
        uvicorn dev_server:app --reload --port 8000
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Optional

from fastapi import Body, FastAPI, Query, Request, Security  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from fastapi.security import HTTPBearer  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from main import handler, router  # noqa: E402

app = FastAPI(title="Facility Incident Management API (dev)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adds the Swagger "Authorize" button so a bearer token can be attached to every "Try it out" call.
# auto_error=False means it never blocks a request itself - real auth is still enforced by main.handler.
bearer_scheme = HTTPBearer(auto_error=False)
AUTH = [Security(bearer_scheme)]

# Request bodies shown in Swagger, matching what each controller actually reads. Every field is
# Optional with an example default: this is documentation only, not enforcement, so intentionally
# incomplete/invalid payloads still reach the real controllers to exercise their own validation.
class RegisterRequest(BaseModel):
    email: Optional[str] = "employee@acme.inc"
    password: Optional[str] = "Passw0rd!"
    full_name: Optional[str] = "Jane Doe"
    role: Optional[str] = None


class LoginRequest(BaseModel):
    email: Optional[str] = "employee@acme.inc"
    password: Optional[str] = "Passw0rd!"


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class CreateEngineerRequest(BaseModel):
    email: Optional[str] = "engineer@acme.inc"
    password: Optional[str] = "Passw0rd!"
    full_name: Optional[str] = "Sam Engineer"
    title: Optional[str] = "HVAC Technician"
    skills: Optional[str] = "hvac,electrical"
    department: Optional[str] = "facilities"
    is_available: Optional[bool] = True


class UpdateEngineerRequest(BaseModel):
    title: Optional[str] = None
    skills: Optional[str] = None
    department: Optional[str] = None
    is_available: Optional[bool] = None


class CreateBuildingRequest(BaseModel):
    name: Optional[str] = "HQ Tower"
    address: Optional[str] = "1 Main St"


class UpdateBuildingRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    is_archived: Optional[bool] = None


class CreateFloorRequest(BaseModel):
    name: Optional[str] = "3rd Floor"


class UpdateFloorRequest(BaseModel):
    name: Optional[str] = None
    is_archived: Optional[bool] = None


class CreateSeatRequest(BaseModel):
    label: Optional[str] = "A-101"


class UpdateSeatRequest(BaseModel):
    label: Optional[str] = None
    is_archived: Optional[bool] = None


class CreateIncidentRequest(BaseModel):
    title: Optional[str] = "AC broken"
    category: Optional[str] = "hvac"  # one of the keys from GET /catalog
    building_id: Optional[int] = 1
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    floor_id: Optional[int] = None
    seat_id: Optional[int] = None


class UpdateIncidentRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    status_reason: Optional[str] = None  # required when blocking, resolving or reopening
    assigned_to: Optional[int] = None
    is_escalated: Optional[bool] = None
    escalation_reason: Optional[str] = None
    building_id: Optional[int] = None
    floor_id: Optional[int] = None
    seat_id: Optional[int] = None


class AssistantRequest(BaseModel):
    message: Optional[str] = "Where do issues happen most?"


class ResetDemoRequest(BaseModel):
    confirm: Optional[str] = "RESET"


class CreateNoteRequest(BaseModel):
    message: Optional[str] = "Its very hot in here"


async def _forward(request: Request) -> Response:
    """Translate an incoming HTTP request into a Lambda event and back into an HTTP response."""
    body_bytes = await request.body()
    event = {
        "rawPath": request.url.path,
        "requestContext": {"http": {"method": request.method}},
        "queryStringParameters": dict(request.query_params) or None,
        "headers": dict(request.headers),
        "body": body_bytes.decode("utf-8") if body_bytes else None,
        "isBase64Encoded": False,
    }
    result = handler(event, None)
    return Response(
        content=result.get("body", ""),
        status_code=result.get("statusCode", 200),
        headers=result.get("headers", {}),
    )


# --- root --------------------------------------------------------------------------------------
@app.get("/", tags=["root"])
async def health_check(request: Request) -> Response:
    return await _forward(request)


# --- auth --------------------------------------------------------------------------------------
@app.post("/auth/register", tags=["auth"])
async def register(request: Request, payload: RegisterRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.post("/auth/login", tags=["auth"])
async def login(request: Request, payload: LoginRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.post("/auth/refresh", tags=["auth"])
async def refresh(request: Request, payload: RefreshRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


# --- users -------------------------------------------------------------------------------------
@app.get("/users/me", tags=["users"], dependencies=AUTH)
async def get_me(request: Request) -> Response:
    return await _forward(request)


# --- catalog -------------------------------------------------------------------------------------
@app.get("/catalog", tags=["catalog"], dependencies=AUTH)
async def get_catalog(request: Request) -> Response:
    return await _forward(request)


# --- engineers -----------------------------------------------------------------------------------
@app.post("/engineers", tags=["engineers"], dependencies=AUTH)
async def create_engineer(request: Request, payload: CreateEngineerRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.get("/engineers", tags=["engineers"], dependencies=AUTH)
async def list_engineers(request: Request) -> Response:
    return await _forward(request)


# Declared before /engineers/{engineer_id} so "workload" isn't parsed as an engineer id.
@app.get("/engineers/workload", tags=["engineers"], dependencies=AUTH)
async def engineer_workload(request: Request, category: Optional[str] = Query(default=None)) -> Response:
    return await _forward(request)


@app.get("/engineers/{engineer_id}", tags=["engineers"], dependencies=AUTH)
async def get_engineer(request: Request, engineer_id: int) -> Response:
    return await _forward(request)


@app.put("/engineers/{engineer_id}", tags=["engineers"], dependencies=AUTH)
async def update_engineer(request: Request, engineer_id: int, payload: UpdateEngineerRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.delete("/engineers/{engineer_id}", tags=["engineers"], dependencies=AUTH)
async def delete_engineer(request: Request, engineer_id: int) -> Response:
    return await _forward(request)


# --- buildings -----------------------------------------------------------------------------------
@app.post("/buildings", tags=["buildings"], dependencies=AUTH)
async def create_building(request: Request, payload: CreateBuildingRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.get("/buildings", tags=["buildings"], dependencies=AUTH)
async def list_buildings(request: Request, include_archived: Optional[bool] = Query(default=None)) -> Response:
    return await _forward(request)


@app.get("/buildings/{building_id}", tags=["buildings"], dependencies=AUTH)
async def get_building(request: Request, building_id: int) -> Response:
    return await _forward(request)


@app.put("/buildings/{building_id}", tags=["buildings"], dependencies=AUTH)
async def update_building(request: Request, building_id: int, payload: UpdateBuildingRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.delete("/buildings/{building_id}", tags=["buildings"], dependencies=AUTH)
async def delete_building(request: Request, building_id: int) -> Response:
    return await _forward(request)


@app.post("/buildings/{building_id}/floors", tags=["buildings"], dependencies=AUTH)
async def create_floor(request: Request, building_id: int, payload: CreateFloorRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.get("/buildings/{building_id}/floors", tags=["buildings"], dependencies=AUTH)
async def list_floors(
    request: Request, building_id: int, include_archived: Optional[bool] = Query(default=None)
) -> Response:
    return await _forward(request)


# --- floors --------------------------------------------------------------------------------------
@app.get("/floors/{floor_id}", tags=["floors"], dependencies=AUTH)
async def get_floor(request: Request, floor_id: int) -> Response:
    return await _forward(request)


@app.put("/floors/{floor_id}", tags=["floors"], dependencies=AUTH)
async def update_floor(request: Request, floor_id: int, payload: UpdateFloorRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.delete("/floors/{floor_id}", tags=["floors"], dependencies=AUTH)
async def delete_floor(request: Request, floor_id: int) -> Response:
    return await _forward(request)


@app.post("/floors/{floor_id}/seats", tags=["floors"], dependencies=AUTH)
async def create_seat(request: Request, floor_id: int, payload: CreateSeatRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.get("/floors/{floor_id}/seats", tags=["floors"], dependencies=AUTH)
async def list_seats(
    request: Request, floor_id: int, include_archived: Optional[bool] = Query(default=None)
) -> Response:
    return await _forward(request)


# --- seats ---------------------------------------------------------------------------------------
@app.get("/seats/{seat_id}", tags=["seats"], dependencies=AUTH)
async def get_seat(request: Request, seat_id: int) -> Response:
    return await _forward(request)


@app.put("/seats/{seat_id}", tags=["seats"], dependencies=AUTH)
async def update_seat(request: Request, seat_id: int, payload: UpdateSeatRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.delete("/seats/{seat_id}", tags=["seats"], dependencies=AUTH)
async def delete_seat(request: Request, seat_id: int) -> Response:
    return await _forward(request)


# --- incidents -----------------------------------------------------------------------------------
@app.post("/incidents", tags=["incidents"], dependencies=AUTH)
async def create_incident(request: Request, payload: CreateIncidentRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.get("/incidents", tags=["incidents"], dependencies=AUTH)
async def list_incidents(
    request: Request,
    status: Optional[str] = Query(default=None, description="Comma-separated, e.g. open,in_progress"),
    priority: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    building_id: Optional[int] = Query(default=None),
    assigned_to: Optional[int] = Query(default=None),
    escalated: Optional[bool] = Query(default=None),
    unassigned: Optional[bool] = Query(default=None),
    archived: Optional[bool] = Query(default=None, description="Admins only: list archived incidents instead"),
    search: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None, description="newest | oldest | updated | priority"),
) -> Response:
    return await _forward(request)


@app.get("/incidents/{incident_id}", tags=["incidents"], dependencies=AUTH)
async def get_incident(request: Request, incident_id: int) -> Response:
    return await _forward(request)


@app.put("/incidents/{incident_id}", tags=["incidents"], dependencies=AUTH)
async def update_incident(request: Request, incident_id: int, payload: UpdateIncidentRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.delete("/incidents/{incident_id}", tags=["incidents"], dependencies=AUTH)
async def delete_incident(request: Request, incident_id: int) -> Response:
    return await _forward(request)


@app.get("/incidents/{incident_id}/timeline", tags=["incidents"], dependencies=AUTH)
async def incident_timeline(request: Request, incident_id: int) -> Response:
    return await _forward(request)


@app.post("/incidents/{incident_id}/notes", tags=["incidents"], dependencies=AUTH)
async def create_note(request: Request, incident_id: int, payload: CreateNoteRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


@app.get("/incidents/{incident_id}/notes", tags=["incidents"], dependencies=AUTH)
async def list_notes(request: Request, incident_id: int) -> Response:
    return await _forward(request)


# --- notes ---------------------------------------------------------------------------------------
@app.delete("/notes/{note_id}", tags=["notes"], dependencies=AUTH)
async def delete_note(request: Request, note_id: int) -> Response:
    return await _forward(request)


# --- dashboard -----------------------------------------------------------------------------------
@app.get("/dashboard/summary", tags=["dashboard"], dependencies=AUTH)
async def dashboard_summary(request: Request) -> Response:
    return await _forward(request)


# --- assistant -----------------------------------------------------------------------------------
@app.get("/assistant", tags=["assistant"], dependencies=AUTH)
async def assistant_suggestions(request: Request) -> Response:
    return await _forward(request)


@app.post("/assistant", tags=["assistant"], dependencies=AUTH)
async def assistant(request: Request, payload: AssistantRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


# --- admin ---------------------------------------------------------------------------------------
@app.post("/admin/reset-demo-data", tags=["admin"], dependencies=AUTH)
async def reset_demo_data(request: Request, payload: ResetDemoRequest = Body(...)) -> Response:
    del payload
    return await _forward(request)


# Fallback for any path not covered above, matching the Lambda handler's own 404 behavior. Kept
# public (no AUTH dependency): the real backend also 404s on unmatched paths before any auth check.
async def _fallback(request: Request) -> Response:
    return await _forward(request)


for _method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
    app.add_api_route("/{full_path:path}", _fallback, methods=[_method], name=f"{_method} fallback", tags=["fallback"])

# Sanity check: warns (doesn't fail) if this file's routes ever drift from the real backend's routes,
# e.g. after adding a new route in routes/*.py without adding the matching explicit operation above.
_documented = {
    (method, route.path)
    for route in app.routes
    if getattr(route, "path", None) != "/{full_path:path}"
    for method in getattr(route, "methods", set())
}
_missing = set(router.routes()) - _documented
if _missing:
    import warnings

    warnings.warn(f"dev_server.py has no explicit route for: {sorted(_missing)} (falls back to generic handling)")
