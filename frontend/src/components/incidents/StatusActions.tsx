import { useState } from 'react';
import type { FormEvent } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import BlockIcon from '@mui/icons-material/Block';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DoneAllIcon from '@mui/icons-material/DoneAll';
import ReplayIcon from '@mui/icons-material/Replay';
import type { ReactElement } from 'react';
import type { IncidentStatus, Role } from '../../types';

const FINISHED: IncidentStatus[] = ['resolved', 'closed'];

const isReopen = (from: IncidentStatus, to: IncidentStatus) => FINISHED.includes(from) && !FINISHED.includes(to);

/** Mirrors the backend rule: blocking, resolving and reopening must be explained to the reporter. */
const requiresReason = (from: IncidentStatus, to: IncidentStatus) =>
  to === 'blocked' || to === 'resolved' || isReopen(from, to);

interface ActionSpec {
  label: string;
  icon: ReactElement;
  color: 'primary' | 'error' | 'success' | 'inherit';
  variant: 'contained' | 'outlined';
  prompt?: string;
}

function describeAction(from: IncidentStatus, to: IncidentStatus, role: Role): ActionSpec {
  if (isReopen(from, to)) {
    return {
      label: role === 'employee' ? 'Still not fixed' : 'Reopen',
      icon: <ReplayIcon />,
      color: 'inherit',
      variant: 'outlined',
      prompt: role === 'employee' ? "What's still wrong?" : 'Why is this incident being reopened?',
    };
  }
  switch (to) {
    case 'in_progress':
      return { label: from === 'blocked' ? 'Resume work' : 'Start work', icon: <PlayArrowIcon />, color: 'primary', variant: 'contained' };
    case 'blocked':
      return { label: 'Mark blocked', icon: <BlockIcon />, color: 'error', variant: 'outlined', prompt: 'What is blocking progress?' };
    case 'resolved':
      return {
        label: 'Mark resolved',
        icon: <CheckCircleIcon />,
        color: 'success',
        variant: 'contained',
        prompt: 'What was done to fix it? This is shared with the person who reported it.',
      };
    case 'closed':
      return { label: role === 'employee' ? 'Yes, confirm & close' : 'Close', icon: <DoneAllIcon />, color: 'success', variant: role === 'employee' ? 'contained' : 'outlined' };
    default:
      return { label: 'Move back to open', icon: <ReplayIcon />, color: 'inherit', variant: 'outlined' };
  }
}

interface StatusActionsProps {
  status: IncidentStatus;
  allowed: IncidentStatus[];
  role: Role;
  disabled?: boolean;
  onChange: (status: IncidentStatus, reason?: string) => Promise<boolean>;
}

/** Workflow buttons for the statuses the current user may move to, with a reason prompt where required. */
export default function StatusActions({ status, allowed, role, disabled, onChange }: StatusActionsProps) {
  const [pending, setPending] = useState<IncidentStatus | null>(null);
  const [reason, setReason] = useState('');

  if (allowed.length === 0) return null;

  const handleClick = (target: IncidentStatus) => {
    if (requiresReason(status, target)) {
      setReason('');
      setPending(target);
    } else {
      onChange(target);
    }
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!pending || !reason.trim()) return;
    if (await onChange(pending, reason.trim())) setPending(null);
  };

  const pendingAction = pending ? describeAction(status, pending, role) : null;

  return (
    <>
      <Box className="flex-row flex-wrap" sx={{ gap: 1 }}>
        {allowed.map((target) => {
          const action = describeAction(status, target, role);
          return (
            <Button
              key={target}
              startIcon={action.icon}
              color={action.color}
              variant={action.variant}
              disabled={disabled}
              onClick={() => handleClick(target)}
            >
              {action.label}
            </Button>
          );
        })}
      </Box>

      <Dialog open={Boolean(pending)} onClose={() => setPending(null)} fullWidth maxWidth="sm">
        <form onSubmit={handleSubmit}>
          <DialogTitle>{pendingAction?.label}</DialogTitle>
          <DialogContent>
            <DialogContentText sx={{ mb: 2 }}>{pendingAction?.prompt}</DialogContentText>
            <TextField
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              fullWidth
              multiline
              minRows={3}
              autoFocus
              required
              label="Explanation"
              helperText="Posted to the incident notes so everyone stays informed."
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setPending(null)}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={disabled || !reason.trim()}>
              Confirm
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </>
  );
}
