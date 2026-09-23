import { Link as RouterLink } from 'react-router-dom';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import LoadChip from '../engineers/LoadChip';
import { useCatalog } from '../../context/CatalogContext';
import type { WorkloadResponse } from '../../types';
import '../../styles/dashboard.css';

/** Active tickets per engineer with availability and load level, heaviest first. */
export default function WorkDistribution({ workload, unassigned }: { workload: WorkloadResponse; unassigned: number }) {
  const { departmentLabel } = useCatalog();
  const engineers = [...workload.engineers].sort((a, b) => b.load_score - a.load_score);
  const available = engineers.filter((engineer) => engineer.is_available).length;

  if (engineers.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No engineers yet. <RouterLink to="/engineers">Add one</RouterLink>.
      </Typography>
    );
  }

  return (
    <div>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {available} of {engineers.length} engineers available · {unassigned} unassigned active ticket{unassigned === 1 ? '' : 's'}
      </Typography>
      <ul className="bar-list">
        {engineers.slice(0, 8).map((engineer) => (
          <li key={engineer.user_id} className="workload-row">
            <span className="bar-label">
              <span className="bar-label-main">{engineer.full_name}</span>
              <span className="bar-label-secondary">{departmentLabel(engineer.department)}</span>
            </span>
            <span className="bar-track" title={`Load score ${engineer.load_score} of ${workload.thresholds.heavy}`}>
              <span
                className={`bar-fill load-${engineer.load_level}`}
                style={{ width: `${Math.max(engineer.load_percent, engineer.active_count ? 4 : 0)}%` }}
              />
            </span>
            {engineer.is_available ? (
              <LoadChip level={engineer.load_level} active={engineer.active_count} />
            ) : (
              <Typography variant="caption" color="text.secondary" className="workload-away">
                Unavailable · {engineer.active_count} active
              </Typography>
            )}
          </li>
        ))}
      </ul>
      <Button component={RouterLink} to="/engineers" size="small" sx={{ mt: 1 }}>
        View workload tracker
      </Button>
    </div>
  );
}
