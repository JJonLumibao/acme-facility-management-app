import { useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import ListSubheader from '@mui/material/ListSubheader';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Chip from '@mui/material/Chip';
import StarIcon from '@mui/icons-material/Star';
import { getWorkload } from '../../services/engineerService';
import { useCatalog } from '../../context/CatalogContext';
import LoadChip from '../engineers/LoadChip';
import type { EngineerWorkload, WorkloadResponse } from '../../types';

interface AssignEngineerSelectProps {
  category: string;
  assignedTo: number | null;
  disabled?: boolean;
  /** Changes whenever the incident is updated, so workload counts are refreshed after (re)assignment. */
  refreshKey?: unknown;
  onAssign: (engineerId: number | null) => void;
}

function EngineerOption({ engineer, departmentLabel }: { engineer: EngineerWorkload; departmentLabel: string }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%', flexWrap: 'wrap' }}>
      <Box sx={{ flex: 1, minWidth: 140 }}>
        <Typography variant="body2" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {engineer.full_name}
          {engineer.recommended && <StarIcon sx={{ fontSize: 16 }} color="primary" titleAccess="Recommended" />}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {departmentLabel}
          {engineer.title ? ` · ${engineer.title}` : ''}
        </Typography>
      </Box>
      {engineer.is_available ? (
        <LoadChip level={engineer.load_level} active={engineer.active_count} />
      ) : (
        <Chip size="small" label="Unavailable" />
      )}
    </Box>
  );
}

/**
 * Engineer picker ranked for this incident's category: same-department and lightly loaded engineers
 * come first, the best candidate is starred, and assigning to an overloaded engineer shows a warning.
 */
export default function AssignEngineerSelect({ category, assignedTo, disabled, refreshKey, onAssign }: AssignEngineerSelectProps) {
  const { departmentLabel } = useCatalog();
  const [workload, setWorkload] = useState<WorkloadResponse | null>(null);

  useEffect(() => {
    getWorkload(category)
      .then(setWorkload)
      .catch(() => setWorkload(null));
  }, [category, refreshKey]);

  const engineers = workload?.engineers ?? [];
  const matching = engineers.filter((engineer) => engineer.department_match);
  const others = engineers.filter((engineer) => !engineer.department_match);
  const assigned = engineers.find((engineer) => engineer.user_id === assignedTo);
  const recommended = engineers.find((engineer) => engineer.recommended);

  const renderGroup = (title: string, group: EngineerWorkload[]) =>
    group.length === 0
      ? []
      : [
          <ListSubheader key={`header-${title}`}>{title}</ListSubheader>,
          ...group.map((engineer) => (
            <MenuItem key={engineer.user_id} value={String(engineer.user_id)} disabled={!engineer.is_available && engineer.user_id !== assignedTo}>
              <EngineerOption engineer={engineer} departmentLabel={departmentLabel(engineer.department)} />
            </MenuItem>
          )),
        ];

  return (
    <Box>
      <TextField
        select
        label="Assigned engineer"
        size="small"
        fullWidth
        value={assignedTo ? String(assignedTo) : ''}
        disabled={disabled || !workload}
        onChange={(e) => onAssign(e.target.value ? Number(e.target.value) : null)}
        slotProps={{
          select: {
            renderValue: (value) =>
              value ? (engineers.find((e) => String(e.user_id) === value)?.full_name ?? 'Assigned') : 'Unassigned',
            displayEmpty: true,
          },
          inputLabel: { shrink: true },
        }}
      >
        <MenuItem value="">
          <em>Unassigned</em>
        </MenuItem>
        {workload?.department
          ? [
              ...renderGroup(`${departmentLabel(workload.department)} (matches category)`, matching),
              ...renderGroup('Other departments', others),
            ]
          : renderGroup('Engineers', engineers)}
      </TextField>

      {!assignedTo && recommended && (
        <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 0.5 }}>
          Suggested: <strong>{recommended.full_name}</strong> ({departmentLabel(recommended.department)},{' '}
          {recommended.active_count} active)
          {' · '}
          <Box
            component="button"
            type="button"
            className="link-button"
            onClick={() => onAssign(recommended.user_id)}
            disabled={disabled}
          >
            Assign
          </Box>
        </Typography>
      )}
      {assigned && assigned.load_level === 'heavy' && (
        <Alert severity="warning" sx={{ mt: 1 }}>
          {assigned.full_name} has a heavy workload ({assigned.active_count} active, {assigned.urgent_count} urgent).
          {recommended && recommended.user_id !== assigned.user_id
            ? ` Consider ${recommended.full_name} (${recommended.active_count} active${recommended.department_match ? ', same department' : ''}).`
            : ''}
        </Alert>
      )}
      {engineers.length > 0 && workload?.department && matching.length === 0 && (
        <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 0.5 }}>
          No engineers in {departmentLabel(workload.department)} yet.
        </Typography>
      )}
    </Box>
  );
}
