import Chip from '@mui/material/Chip';
import type { LoadLevel } from '../../types';

const LOAD_META: Record<LoadLevel, { label: string; color: 'success' | 'warning' | 'error' }> = {
  light: { label: 'Light load', color: 'success' },
  moderate: { label: 'Moderate load', color: 'warning' },
  heavy: { label: 'Heavy load', color: 'error' },
};

/** Workload level chip (always labelled, never color alone). */
export default function LoadChip({ level, active }: { level: LoadLevel; active?: number }) {
  const meta = LOAD_META[level];
  return (
    <Chip
      size="small"
      variant="outlined"
      color={meta.color}
      label={active === undefined ? meta.label : `${meta.label} · ${active} active`}
      sx={{ fontWeight: 600 }}
    />
  );
}
