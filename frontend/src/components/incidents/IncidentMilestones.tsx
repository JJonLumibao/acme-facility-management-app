import { useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tooltip from '@mui/material/Tooltip';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import TimerOutlinedIcon from '@mui/icons-material/TimerOutlined';
import type { Incident } from '../../types';
import { formatDateTime, formatHours, hoursBetween } from '../../utils/format';
import '../../styles/incidents.css';

const MILESTONES: Array<{ key: keyof Incident; label: string; hint: string }> = [
  { key: 'created_at', label: 'Reported', hint: 'Incident submitted' },
  { key: 'acknowledged_at', label: 'Acknowledged', hint: 'First response from an admin or engineer' },
  { key: 'assigned_at', label: 'Assigned', hint: 'First assigned to an engineer' },
  { key: 'started_at', label: 'Work started', hint: 'Engineer first started working on it' },
  { key: 'resolved_at', label: 'Resolved', hint: 'Marked as fixed' },
  { key: 'closed_at', label: 'Closed', hint: 'Resolution confirmed and ticket closed' },
];

/** Re-render every minute so elapsed times on open incidents stay current. */
function useMinuteTick(enabled: boolean) {
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    const interval = setInterval(() => setTick((tick) => tick + 1), 60_000);
    return () => clearInterval(interval);
  }, [enabled]);
}

/** Time tracking: when each lifecycle milestone happened and how long after the report it took. */
export default function IncidentMilestones({ incident }: { incident: Incident }) {
  const isFinished = Boolean(incident.resolved_at || incident.closed_at);
  useMinuteTick(!isFinished);

  const totalHours = hoursBetween(incident.created_at, incident.resolved_at ?? incident.closed_at);

  return (
    <div>
      <Box className="milestone-summary">
        <TimerOutlinedIcon color={isFinished ? 'success' : 'primary'} />
        <div>
          <Typography variant="h5" component="p" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
            {formatHours(totalHours)}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {isFinished ? 'Total time to resolve' : 'Open so far'}
          </Typography>
        </div>
      </Box>
      <ol className="milestone-list">
        {MILESTONES.map((milestone) => {
          const timestamp = incident[milestone.key] as string | null;
          return (
            <li key={milestone.key} className={timestamp ? 'milestone-done' : 'milestone-pending'}>
              {timestamp ? (
                <CheckCircleIcon fontSize="small" color="success" />
              ) : (
                <RadioButtonUncheckedIcon fontSize="small" color="disabled" />
              )}
              <Tooltip title={milestone.hint} placement="top-start">
                <span className="milestone-label">{milestone.label}</span>
              </Tooltip>
              <span className="milestone-value">
                {timestamp ? (
                  <Tooltip title={formatDateTime(timestamp)}>
                    <span>
                      {milestone.key === 'created_at'
                        ? new Date(timestamp).toLocaleDateString()
                        : `+${formatHours(hoursBetween(incident.created_at, timestamp))}`}
                    </span>
                  </Tooltip>
                ) : (
                  '—'
                )}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
