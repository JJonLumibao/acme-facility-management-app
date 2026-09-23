import Typography from '@mui/material/Typography';
import Tooltip from '@mui/material/Tooltip';
import type { DashboardSummary } from '../../types';
import { formatHours } from '../../utils/format';
import '../../styles/dashboard.css';

const STAGES: Array<{ key: keyof DashboardSummary['response_times']; label: string; hint: string }> = [
  { key: 'acknowledge', label: 'Acknowledge', hint: 'Report → first admin/engineer response' },
  { key: 'assign', label: 'Assign', hint: 'Report → first engineer assignment' },
  { key: 'start', label: 'Start work', hint: 'Report → engineer starts work' },
  { key: 'resolve', label: 'Resolve', hint: 'Report → marked resolved' },
];

/** Median (and average) time from report to each lifecycle milestone. */
export default function ResponseTimes({ times }: { times: DashboardSummary['response_times'] }) {
  return (
    <div className="response-times">
      {STAGES.map((stage) => {
        const stat = times[stage.key];
        return (
          <Tooltip key={stage.key} title={stage.hint} placement="top">
            <div className="response-time" tabIndex={0}>
              <Typography variant="body2" color="text.secondary">
                {stage.label}
              </Typography>
              <Typography variant="h5" component="p" sx={{ fontWeight: 700 }}>
                {formatHours(stat.median_hours)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {stat.count ? `median · avg ${formatHours(stat.avg_hours)} · ${stat.count} tickets` : 'no data yet'}
              </Typography>
            </div>
          </Tooltip>
        );
      })}
    </div>
  );
}
