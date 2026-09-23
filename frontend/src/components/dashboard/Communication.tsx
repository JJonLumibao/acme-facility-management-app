import Typography from '@mui/material/Typography';
import Tooltip from '@mui/material/Tooltip';
import type { CommunicationStats } from '../../types';
import { formatHours } from '../../utils/format';
import '../../styles/dashboard.css';

interface Metric {
  label: string;
  value: string;
  hint: string;
  warn?: boolean;
}

/** How well reporters are kept informed about their tickets. */
export default function Communication({ stats }: { stats: CommunicationStats }) {
  const metrics: Metric[] = [
    {
      label: 'Tickets with a staff update',
      value: stats.staff_update_rate === null ? '—' : `${stats.staff_update_rate}%`,
      hint: `${stats.with_staff_update} of ${stats.total} tickets have at least one note from an admin or engineer`,
      warn: stats.staff_update_rate !== null && stats.staff_update_rate < 80,
    },
    {
      label: 'First staff reply',
      value: formatHours(stats.avg_first_response_hours),
      hint: 'Average time from report to the first note from an admin or engineer',
    },
    {
      label: 'Resolved with an explanation',
      value: stats.finished_with_update_rate === null ? '—' : `${stats.finished_with_update_rate}%`,
      hint: `Of ${stats.finished} resolved/closed tickets, share where staff left a note for the reporter`,
      warn: stats.finished_with_update_rate !== null && stats.finished_with_update_rate < 90,
    },
    {
      label: `No update in ${stats.stale_after_hours}h`,
      value: String(stats.stale_active),
      hint: 'Active tickets with no activity recently - reporters may be left wondering',
      warn: stats.stale_active > 0,
    },
    {
      label: 'Reopened',
      value: String(stats.reopened),
      hint: 'Tickets reopened after being resolved - the fix did not stick or was not explained',
      warn: stats.reopened > 0,
    },
  ];

  return (
    <div className="metric-grid">
      {metrics.map((metric) => (
        <Tooltip key={metric.label} title={metric.hint} placement="top">
          <div className="metric" tabIndex={0}>
            <Typography variant="h5" component="p" sx={{ fontWeight: 700 }} color={metric.warn ? 'warning.dark' : 'text.primary'}>
              {metric.value}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {metric.label}
            </Typography>
          </div>
        </Tooltip>
      ))}
    </div>
  );
}
