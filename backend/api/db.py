"""PostgreSQL connection management and schema initialization."""
import logging
import os
import time
from typing import Any, Dict, List, Optional

from psycopg import OperationalError, connect

logger = logging.getLogger(__name__)

# Aurora Serverless v2 auto-pauses when idle and takes ~15s+ to resume on the next connection.
# 25s leaves room for that while staying under CloudFront's 30s origin timeout.
CONNECT_TIMEOUT_SECONDS = 25

_CONFIG = (
    f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"user={os.getenv('POSTGRES_USER', 'test')} "
    f"password={os.getenv('POSTGRES_PASS', 'test')} "
    f"dbname={os.getenv('POSTGRES_NAME', 'test')} "
    f"connect_timeout={CONNECT_TIMEOUT_SECONDS}"
)
if os.getenv("IS_LOCAL", "true") != "true":
    _CONFIG += " sslmode=require"

_CONN: Optional[Any] = None
_SCHEMA_READY = False

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('employee', 'facility_admin', 'engineer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS engineer_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    skills TEXT,
    is_available BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buildings (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS floors (
    id SERIAL PRIMARY KEY,
    building_id INTEGER NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS seats (
    id SERIAL PRIMARY KEY,
    floor_id INTEGER NOT NULL REFERENCES floors(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'blocked', 'resolved', 'closed')),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    building_id INTEGER REFERENCES buildings(id),
    floor_id INTEGER REFERENCES floors(id),
    seat_id INTEGER REFERENCES seats(id),
    reported_by INTEGER NOT NULL REFERENCES users(id),
    assigned_to INTEGER REFERENCES users(id),
    is_escalated BOOLEAN NOT NULL DEFAULT false,
    escalation_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS incident_notes (
    id SERIAL PRIMARY KEY,
    incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES users(id),
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Incremental migrations: safe to re-run, and upgrade databases created before these columns existed.
ALTER TABLE engineer_profiles ADD COLUMN IF NOT EXISTS department TEXT;

-- Archived locations are hidden from new reports; archiving cascades to floors, seats and incidents.
ALTER TABLE buildings ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE floors ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE seats ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT false;
-- Incidents are archived together with their location (see facility_model.set_archived).
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS blocked_reason TEXT,
    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

-- Audit trail of every change to an incident; powers the timeline and response-time reporting.
CREATE TABLE IF NOT EXISTS incident_events (
    id SERIAL PRIMARY KEY,
    incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    from_value TEXT,
    to_value TEXT,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_incident_events_incident ON incident_events(incident_id, created_at);
CREATE INDEX IF NOT EXISTS idx_incident_notes_incident ON incident_notes(incident_id, created_at);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_assigned_to ON incidents(assigned_to);
CREATE INDEX IF NOT EXISTS idx_incidents_reported_by ON incidents(reported_by);
"""


def get_connection() -> Any:
    """Return a pooled PostgreSQL connection, reconnecting if necessary."""
    global _CONN
    if _CONN is None or _CONN.closed:
        started = time.monotonic()
        try:
            _CONN = connect(_CONFIG, autocommit=True)
        except OperationalError as exc:
            # A resuming database can refuse connections briefly; retry once if there's still time
            # before CloudFront gives up (a full timeout has already used the whole budget).
            if time.monotonic() - started > 10:
                raise
            logger.warning("Database connection failed (%s); retrying once", exc)
            time.sleep(2)
            _CONN = connect(_CONFIG, autocommit=True)
    return _CONN


def transaction() -> Any:
    """Group several model calls into one atomic unit: `with transaction(): ...`."""
    return get_connection().transaction()


def init_schema() -> None:
    """Create tables if they do not exist yet. Safe to call on every cold start."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    _SCHEMA_READY = True


def row_to_dict(cur: Any, row: Optional[tuple]) -> Optional[Dict[str, Any]]:
    """Convert a single fetched row into a dict keyed by column name."""
    if row is None:
        return None
    columns = [col[0] for col in cur.description]
    return dict(zip(columns, row))


def rows_to_dicts(cur: Any, rows: List[tuple]) -> List[Dict[str, Any]]:
    """Convert a list of fetched rows into a list of dicts keyed by column name."""
    columns = [col[0] for col in cur.description]
    return [dict(zip(columns, row)) for row in rows]
