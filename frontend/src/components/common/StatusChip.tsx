import Chip from '@mui/material/Chip';
import { STATUS_COLORS } from '../../styles/theme';
import { STATUS_LABELS } from '../../utils/format';
import type { IncidentStatus } from '../../types';

/** Colored chip representing an incident's workflow status. */
export default function StatusChip({ status }: { status: IncidentStatus }) {
  return (
    <Chip
      label={STATUS_LABELS[status]}
      size="small"
      sx={{
        backgroundColor: `${STATUS_COLORS[status]}1a`,
        color: STATUS_COLORS[status],
        fontWeight: 600,
      }}
    />
  );
}
