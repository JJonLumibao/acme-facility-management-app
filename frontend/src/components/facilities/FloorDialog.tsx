import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import ErrorAlert from '../common/ErrorAlert';
import { ApiError } from '../../services/apiClient';
import { createFloor, updateFloor } from '../../services/facilityService';
import type { Floor } from '../../types';

interface FloorDialogProps {
  open: boolean;
  buildingId: number | null;
  floor: Floor | null;
  onClose: () => void;
  onSaved: (floor: Floor) => void;
}

/** Create/edit dialog for a floor within a building. */
export default function FloorDialog({ open, buildingId, floor, onClose, onSaved }: FloorDialogProps) {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setName(floor?.name ?? '');
      setError(null);
    }
  }, [open, floor]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!buildingId && !floor) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const saved = floor ? await updateFloor(floor.id, { name }) : await createFloor(buildingId as number, { name });
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to save floor.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <form onSubmit={handleSubmit}>
        <DialogTitle>{floor ? 'Edit floor' : 'Add floor'}</DialogTitle>
        <DialogContent>
          <ErrorAlert message={error} />
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            fullWidth
            autoFocus
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={isSubmitting || !name}>
            Save
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
