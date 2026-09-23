import { Link as RouterLink } from 'react-router-dom';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import PriorityHighIcon from '@mui/icons-material/PriorityHigh';
import BlockIcon from '@mui/icons-material/Block';
import StatusChip from '../common/StatusChip';
import PriorityChip from '../common/PriorityChip';
import type { AttentionItem } from '../../types';
import { timeAgo } from '../../utils/format';
import '../../styles/dashboard.css';

/** Escalated or blocked incidents, each with the reason it needs attention. */
export default function AttentionList({ items }: { items: AttentionItem[] }) {
  if (items.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        Nothing escalated or blocked right now.
      </Typography>
    );
  }

  return (
    <ul className="attention-list">
      {items.map((item) => (
        <li key={item.id}>
          <RouterLink to={`/incidents/${item.id}`} className="attention-item">
            <div className="attention-head">
              <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>
                #{item.id} {item.title}
              </Typography>
              <span className="flex-row" style={{ gap: 6 }}>
                <StatusChip status={item.status} />
                <PriorityChip priority={item.priority} />
              </span>
            </div>
            {item.is_escalated && (
              <Typography variant="body2" color="text.secondary" className="attention-reason">
                <Chip icon={<PriorityHighIcon />} label="Escalated" size="small" color="error" variant="outlined" />
                {item.escalation_reason || 'No reason given'}
              </Typography>
            )}
            {item.status === 'blocked' && (
              <Typography variant="body2" color="text.secondary" className="attention-reason">
                <Chip icon={<BlockIcon />} label="Blocked" size="small" color="warning" variant="outlined" />
                {item.blocked_reason || 'No reason given'}
              </Typography>
            )}
            <Typography variant="caption" color="text.secondary">
              {item.assignee_name ? `Assigned to ${item.assignee_name}` : 'Unassigned'}
              {item.building_name ? ` · ${item.building_name}` : ''} · reported {timeAgo(item.created_at)}
            </Typography>
          </RouterLink>
        </li>
      ))}
    </ul>
  );
}
