import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import ErrorAlert from '../common/ErrorAlert';
import { ApiError } from '../../services/apiClient';
import { createSeat, updateSeat } from '../../services/facilityService';
import type { Seat } from '../../types';

interface SeatDialogProps {
  open: boolean;
  floorId: number | null;
  seat: Seat | null;
  onClose: () => void;
  onSaved: (seat: Seat) => void;
}

/** Create/edit dialog for a seat within a floor. */
export default function SeatDialog({ open, floorId, seat, onClose, onSaved }: SeatDialogProps) {
  const [label, setLabel] = useState('');
  const [isArchived, setIsArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setLabel(seat?.label ?? '');
      setIsArchived(seat?.is_archived ?? false);
      setError(null);
    }
  }, [open, seat]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!floorId && !seat) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const saved = seat ? await updateSeat(seat.id, { label, is_archived: isArchived }) : await createSeat(floorId as number, { label });
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to save seat.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <form onSubmit={handleSubmit}>
        <DialogTitle>{seat ? 'Edit seat' : 'Add seat'}</DialogTitle>
        <DialogContent>
          <ErrorAlert message={error} />
          <TextField
            label="Label"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            required
            fullWidth
            autoFocus
            sx={{ mt: 1 }}
          />
          {seat && (
            <FormControlLabel
              sx={{ mt: 1 }}
              control={<Switch checked={isArchived} onChange={(e) => setIsArchived(e.target.checked)} />}
              label="Archived (also archives incidents reported at this seat)"
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={isSubmitting || !label}>
            Save
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
