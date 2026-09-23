import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import ErrorAlert from '../common/ErrorAlert';
import { ApiError } from '../../services/apiClient';
import { createBuilding, updateBuilding } from '../../services/facilityService';
import type { Building } from '../../types';

interface BuildingDialogProps {
  open: boolean;
  building: Building | null;
  onClose: () => void;
  onSaved: (building: Building) => void;
}

/** Create/edit dialog for a building. */
export default function BuildingDialog({ open, building, onClose, onSaved }: BuildingDialogProps) {
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setName(building?.name ?? '');
      setAddress(building?.address ?? '');
      setError(null);
    }
  }, [open, building]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const saved = building
        ? await updateBuilding(building.id, { name, address })
        : await createBuilding({ name, address: address || undefined });
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to save building.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <form onSubmit={handleSubmit}>
        <DialogTitle>{building ? 'Edit building' : 'Add building'}</DialogTitle>
        <DialogContent>
          <ErrorAlert message={error} />
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} required fullWidth autoFocus />
            <TextField label="Address" value={address} onChange={(e) => setAddress(e.target.value)} fullWidth />
          </Stack>
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
