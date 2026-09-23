import { useState } from 'react';
import type { FormEvent } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import PriorityHighIcon from '@mui/icons-material/PriorityHigh';

interface EscalationControlProps {
  isEscalated: boolean;
  disabled?: boolean;
  onEscalate: (reason: string) => Promise<boolean>;
  onDeescalate: () => void;
}

/** Escalate (with a required reason) or remove an existing escalation. */
export default function EscalationControl({ isEscalated, disabled, onEscalate, onDeescalate }: EscalationControlProps) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (reason.trim() && (await onEscalate(reason.trim()))) {
      setOpen(false);
      setReason('');
    }
  };

  if (isEscalated) {
    return (
      <Button variant="text" color="inherit" disabled={disabled} onClick={onDeescalate}>
        Remove escalation
      </Button>
    );
  }

  return (
    <>
      <Button variant="outlined" color="error" startIcon={<PriorityHighIcon />} disabled={disabled} onClick={() => setOpen(true)}>
        Escalate
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <form onSubmit={handleSubmit}>
          <DialogTitle>Escalate this incident</DialogTitle>
          <DialogContent>
            <DialogContentText sx={{ mb: 2 }}>
              Escalated incidents are highlighted to facility admins. Tell them why this needs extra attention.
            </DialogContentText>
            <TextField
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              label="Reason"
              placeholder="e.g. Affects the whole floor, no response for 2 days"
              fullWidth
              multiline
              minRows={2}
              autoFocus
              required
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained" color="error" disabled={disabled || !reason.trim()}>
              Escalate
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </>
  );
}
