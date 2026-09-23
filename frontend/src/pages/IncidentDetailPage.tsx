import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import CircularProgress from '@mui/material/CircularProgress';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import DeleteIcon from '@mui/icons-material/Delete';
import { useAuth } from '../context/AuthContext';
import { useCatalog } from '../context/CatalogContext';
import { deleteIncident, getIncident, updateIncident } from '../services/incidentService';
import type { UpdateIncidentPayload } from '../services/incidentService';
import { ApiError } from '../services/apiClient';
import ErrorAlert from '../components/common/ErrorAlert';
import ConfirmDialog from '../components/common/ConfirmDialog';
import StatusChip from '../components/common/StatusChip';
import PriorityChip from '../components/common/PriorityChip';
import CategoryIcon from '../components/incidents/CategoryIcon';
import IncidentWorkflow from '../components/incidents/IncidentWorkflow';
import IncidentMilestones from '../components/incidents/IncidentMilestones';
import IncidentTimeline from '../components/incidents/IncidentTimeline';
import StatusActions from '../components/incidents/StatusActions';
import AssignEngineerSelect from '../components/incidents/AssignEngineerSelect';
import EscalationControl from '../components/incidents/EscalationControl';
import NoteThread from '../components/incidents/NoteThread';
import { ACTIVE_STATUSES, INCIDENT_PRIORITIES } from '../types';
import type { Incident, IncidentStatus } from '../types';
import { PRIORITY_LABELS, formatDateTime, formatLocation, timeAgo } from '../utils/format';
import '../styles/incidents.css';

export default function IncidentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { categoryLabel, departmentLabel, getCategory } = useCatalog();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  // Bumped after every change so the timeline, notes and workload re-fetch.
  const [version, setVersion] = useState(0);

  const incidentId = Number(id);

  useEffect(() => {
    setIsLoading(true);
    getIncident(incidentId)
      .then(setIncident)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Unable to load incident.'))
      .finally(() => setIsLoading(false));
  }, [incidentId]);

  const applyUpdate = useCallback(
    async (changes: UpdateIncidentPayload): Promise<boolean> => {
      setIsSaving(true);
      setError(null);
      try {
        setIncident(await updateIncident(incidentId, changes));
        setVersion((v) => v + 1);
        return true;
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Unable to update incident.');
        return false;
      } finally {
        setIsSaving(false);
      }
    },
    [incidentId],
  );

  const handleDelete = async () => {
    try {
      await deleteIncident(incidentId);
      navigate('/incidents');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to delete incident.');
      setConfirmDelete(false);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!incident || !user) {
    return (
      <Box className="page-container">
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/incidents')} sx={{ mb: 2 }}>
          Back to incidents
        </Button>
        <ErrorAlert message={error ?? 'Incident not found.'} />
      </Box>
    );
  }

  const isAdmin = user.role === 'facility_admin';
  const isReporter = user.role === 'employee' && incident.reported_by === user.id;
  // Archived incidents (their location was archived) are read-only for everyone.
  const isActive = ACTIVE_STATUSES.includes(incident.status) && !incident.is_archived;
  const allowed = incident.allowed_transitions ?? [];
  const changeStatus = (status: IncidentStatus, reason?: string) => applyUpdate({ status, status_reason: reason });
  const canEditPriority = (isAdmin && !incident.is_archived) || (isReporter && isActive);
  const canEscalate = (isAdmin || isReporter) && isActive;
  const awaitingConfirmation = isReporter && incident.status === 'resolved' && !incident.is_archived;
  const category = getCategory(incident.category);

  return (
    <Box className="page-container">
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)} sx={{ mb: 2 }}>
        Back
      </Button>

      <ErrorAlert message={error} />

      <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
        <Box className="flex-between" sx={{ flexWrap: 'wrap', gap: 1, alignItems: 'flex-start' }}>
          <Typography variant="h4" component="h1" sx={{ fontSize: { xs: '1.5rem', sm: '2rem' } }}>
            <span className="incident-id">#{incident.id}</span> {incident.title}
          </Typography>
          <Box className="flex-row" sx={{ gap: 1 }}>
            <StatusChip status={incident.status} />
            <PriorityChip priority={incident.priority} />
          </Box>
        </Box>

        <dl className="incident-facts">
          <div>
            <dt>Category</dt>
            <dd className="flex-row" style={{ gap: 6 }}>
              <CategoryIcon category={incident.category} fontSize="small" color="action" />
              {categoryLabel(incident.category)}
            </dd>
          </div>
          <div>
            <dt>Location</dt>
            <dd>{formatLocation([incident.building_name, incident.floor_name, incident.seat_label])}</dd>
          </div>
          <div>
            <dt>Reported by</dt>
            <dd>
              {incident.reporter_name ?? '—'} · <span title={formatDateTime(incident.created_at)}>{timeAgo(incident.created_at)}</span>
            </dd>
          </div>
          <div>
            <dt>Assigned to</dt>
            <dd>{incident.assignee_name ?? 'Not yet assigned'}</dd>
          </div>
          {category?.department && (
            <div>
              <dt>Handled by</dt>
              <dd>{departmentLabel(category.department)}</dd>
            </div>
          )}
        </dl>

        {incident.description && (
          <Typography variant="body1" sx={{ mt: 2, whiteSpace: 'pre-wrap' }}>
            {incident.description}
          </Typography>
        )}

        {incident.is_archived && (
          <Alert severity="info" sx={{ mt: 2 }}>
            This incident is archived because its location was archived. It&apos;s read-only until the location is
            restored.
          </Alert>
        )}
        {incident.is_escalated && (
          <Alert severity="error" sx={{ mt: 2 }}>
            <AlertTitle>Escalated</AlertTitle>
            {incident.escalation_reason || 'No reason given.'}
          </Alert>
        )}
        {incident.status === 'blocked' && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            <AlertTitle>Blocked</AlertTitle>
            {incident.blocked_reason || 'No reason given.'}
          </Alert>
        )}

        <IncidentWorkflow status={incident.status} />
      </Paper>

      {awaitingConfirmation && (
        <Alert severity="success" sx={{ mb: 3 }} icon={false}>
          <AlertTitle>This incident was marked as resolved</AlertTitle>
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            Check the latest note for what was done. Is the problem fixed?
          </Typography>
          <StatusActions status={incident.status} allowed={allowed} role={user.role} disabled={isSaving} onChange={changeStatus} />
        </Alert>
      )}

      <div className="incident-detail-grid">
        <div className="flex-col">
          {!awaitingConfirmation && !incident.is_archived && (allowed.length > 0 || isAdmin || canEditPriority || canEscalate) && (
            <Paper sx={{ p: { xs: 2, sm: 3 } }}>
              <Typography variant="h6" gutterBottom>
                Actions
              </Typography>
              <div className="flex-col">
                <StatusActions status={incident.status} allowed={allowed} role={user.role} disabled={isSaving} onChange={changeStatus} />
                {isAdmin && (
                  <AssignEngineerSelect
                    category={incident.category}
                    assignedTo={incident.assigned_to}
                    disabled={isSaving}
                    refreshKey={version}
                    onAssign={(engineerId) => applyUpdate({ assigned_to: engineerId })}
                  />
                )}
                {(canEditPriority || canEscalate) && (
                  <Box className="flex-row flex-wrap" sx={{ gap: 2 }}>
                    {canEditPriority && (
                      <TextField
                        select
                        label="Priority"
                        size="small"
                        value={incident.priority}
                        disabled={isSaving}
                        onChange={(e) => applyUpdate({ priority: e.target.value })}
                        sx={{ minWidth: 160 }}
                      >
                        {INCIDENT_PRIORITIES.map((priority) => (
                          <MenuItem key={priority} value={priority}>
                            {PRIORITY_LABELS[priority]}
                          </MenuItem>
                        ))}
                      </TextField>
                    )}
                    {canEscalate && (
                      <EscalationControl
                        isEscalated={incident.is_escalated}
                        disabled={isSaving}
                        onEscalate={(reason) => applyUpdate({ is_escalated: true, escalation_reason: reason })}
                        onDeescalate={() => applyUpdate({ is_escalated: false })}
                      />
                    )}
                  </Box>
                )}
                {isAdmin && (
                  <Box>
                    <Button color="error" size="small" startIcon={<DeleteIcon />} onClick={() => setConfirmDelete(true)}>
                      Delete incident
                    </Button>
                  </Box>
                )}
              </div>
            </Paper>
          )}

          <Paper sx={{ p: { xs: 2, sm: 3 } }}>
            <NoteThread
              incidentId={incidentId}
              currentUser={user}
              isReadOnly={incident.is_archived || (incident.status === 'closed' && !isAdmin)}
              refreshKey={version}
              onNoteAdded={() => {
                // A staff reply can stamp the "acknowledged" milestone, so refresh the incident too.
                getIncident(incidentId).then(setIncident).catch(() => undefined);
                setVersion((v) => v + 1);
              }}
            />
          </Paper>
        </div>

        <div className="flex-col">
          <Paper sx={{ p: { xs: 2, sm: 3 } }}>
            <Typography variant="h6" gutterBottom>
              Time tracking
            </Typography>
            <IncidentMilestones incident={incident} />
          </Paper>
          <Paper sx={{ p: { xs: 2, sm: 3 } }}>
            <Typography variant="h6" gutterBottom>
              Activity
            </Typography>
            <IncidentTimeline incidentId={incidentId} refreshKey={version} />
          </Paper>
        </div>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete incident"
        message="This permanently removes the incident, its notes and its history. Continue?"
        onCancel={() => setConfirmDelete(false)}
        onConfirm={handleDelete}
      />
    </Box>
  );
}
