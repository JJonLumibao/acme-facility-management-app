import Chip from '@mui/material/Chip';
import { PRIORITY_COLORS } from '../../styles/theme';
import type { IncidentPriority } from '../../types';

/** Colored outlined chip representing an incident's priority level. */
export default function PriorityChip({ priority }: { priority: IncidentPriority }) {
  return (
    <Chip
      label={priority.charAt(0).toUpperCase() + priority.slice(1)}
      size="small"
      variant="outlined"
      sx={{
        borderColor: PRIORITY_COLORS[priority],
        color: PRIORITY_COLORS[priority],
        fontWeight: 600,
      }}
    />
  );
}
