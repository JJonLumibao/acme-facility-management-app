import { useEffect, useState } from 'react';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Tooltip from '@mui/material/Tooltip';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutlineOutlined';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import PersonAddAltIcon from '@mui/icons-material/PersonAddAlt';
import PersonRemoveIcon from '@mui/icons-material/PersonRemove';
import FlagIcon from '@mui/icons-material/Flag';
import PriorityHighIcon from '@mui/icons-material/PriorityHigh';
import EditNoteIcon from '@mui/icons-material/EditNote';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutlineOutlined';
import type { ReactElement } from 'react';
import { getIncidentTimeline } from '../../services/incidentService';
import ErrorAlert from '../common/ErrorAlert';
import type { IncidentEvent, IncidentPriority, IncidentStatus } from '../../types';
import { PRIORITY_LABELS, STATUS_LABELS, formatDateTime, timeAgo } from '../../utils/format';
import '../../styles/incidents.css';

const statusLabel = (value: string | null) => (value ? (STATUS_LABELS[value as IncidentStatus] ?? value) : '');
const priorityLabel = (value: string | null) => (value ? (PRIORITY_LABELS[value as IncidentPriority] ?? value) : '');

function describe(event: IncidentEvent): { icon: ReactElement; text: string } {
  switch (event.event_type) {
    case 'created':
      return { icon: <AddCircleOutlineIcon fontSize="small" />, text: 'reported the incident' };
    case 'status_changed':
      return {
        icon: <SwapHorizIcon fontSize="small" />,
        text: `moved it from ${statusLabel(event.from_value)} to ${statusLabel(event.to_value)}`,
      };
    case 'assigned':
      return {
        icon: <PersonAddAltIcon fontSize="small" />,
        text: event.from_value ? `reassigned it from ${event.from_value} to ${event.to_value}` : `assigned it to ${event.to_value}`,
      };
    case 'unassigned':
      return { icon: <PersonRemoveIcon fontSize="small" />, text: `unassigned ${event.from_value ?? 'the engineer'}` };
    case 'priority_changed':
      return {
        icon: <FlagIcon fontSize="small" />,
        text: `changed priority from ${priorityLabel(event.from_value)} to ${priorityLabel(event.to_value)}`,
      };
    case 'escalated':
      return { icon: <PriorityHighIcon fontSize="small" color="error" />, text: 'escalated the incident' };
    case 'deescalated':
      return { icon: <PriorityHighIcon fontSize="small" />, text: 'removed the escalation' };
    case 'details_updated':
      return { icon: <EditNoteIcon fontSize="small" />, text: `updated ${event.details ?? 'details'}` };
    case 'note_added':
      return { icon: <ChatBubbleOutlineIcon fontSize="small" />, text: 'added a note' };
    default:
      return { icon: <EditNoteIcon fontSize="small" />, text: event.event_type };
  }
}

/** Chronological activity log for an incident (who did what, and when). */
export default function IncidentTimeline({ incidentId, refreshKey }: { incidentId: number; refreshKey?: unknown }) {
  const [events, setEvents] = useState<IncidentEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getIncidentTimeline(incidentId)
      .then((loaded) => {
        setEvents(loaded);
        setError(null);
      })
      .catch(() => setError('Unable to load activity.'));
  }, [incidentId, refreshKey]);

  if (error) return <ErrorAlert message={error} />;
  if (!events) return <CircularProgress size={24} />;
  if (events.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No activity recorded yet.
      </Typography>
    );
  }

  return (
    <ol className="timeline">
      {events.map((event) => {
        const { icon, text } = describe(event);
        const showDetails = event.details && event.event_type !== 'details_updated';
        return (
          <li key={event.id} className="timeline-item">
            <span className="timeline-icon">{icon}</span>
            <div className="timeline-body">
              <Typography variant="body2">
                <strong>{event.actor_name ?? 'Someone'}</strong> {text}
              </Typography>
              {showDetails && (
                <Typography variant="body2" color="text.secondary" className="timeline-details">
                  “{event.details}”
                </Typography>
              )}
              <Tooltip title={formatDateTime(event.created_at)}>
                <Typography variant="caption" color="text.secondary">
                  {timeAgo(event.created_at)}
                </Typography>
              </Tooltip>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
