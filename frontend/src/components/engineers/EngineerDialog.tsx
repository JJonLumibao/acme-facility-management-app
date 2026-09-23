import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import ErrorAlert from '../common/ErrorAlert';
import { ApiError } from '../../services/apiClient';
import { createEngineer, updateEngineer } from '../../services/engineerService';
import { useCatalog } from '../../context/CatalogContext';
import type { EngineerProfile } from '../../types';

interface EngineerDialogProps {
  open: boolean;
  engineer: EngineerProfile | null;
  onClose: () => void;
  onSaved: () => void;
}

/** Create/edit dialog for engineer profiles. Account fields only apply when creating. */
export default function EngineerDialog({ open, engineer, onClose, onSaved }: EngineerDialogProps) {
  const { catalog } = useCatalog();
  const isEditing = Boolean(engineer);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [title, setTitle] = useState('');
  const [skills, setSkills] = useState('');
  const [department, setDepartment] = useState('');
  const [isAvailable, setIsAvailable] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setEmail(engineer?.email ?? '');
      setPassword('');
      setFullName(engineer?.full_name ?? '');
      setTitle(engineer?.title ?? '');
      setSkills(engineer?.skills ?? '');
      setDepartment(engineer?.department ?? '');
      setIsAvailable(engineer?.is_available ?? true);
      setError(null);
    }
  }, [open, engineer]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const profile = { title, skills, department: department || null, is_available: isAvailable };
      if (isEditing && engineer) {
        await updateEngineer(engineer.user_id, profile);
      } else {
        await createEngineer({ email, password, full_name: fullName, ...profile });
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to save engineer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <form onSubmit={handleSubmit}>
        <DialogTitle>{isEditing ? 'Edit engineer' : 'Add engineer'}</DialogTitle>
        <DialogContent>
          <ErrorAlert message={error} />
          <Stack spacing={2} sx={{ mt: 1 }}>
            {!isEditing && (
              <>
                <TextField label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} required fullWidth autoFocus />
                <TextField
                  label="Email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  fullWidth
                  placeholder="name@acme.inc"
                />
                <TextField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required fullWidth />
              </>
            )}
            <TextField
              select
              label="Department"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              fullWidth
              helperText="Used to suggest the right engineer for each incident category"
            >
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
              {catalog?.departments.map((d) => (
                <MenuItem key={d.key} value={d.key}>
                  {d.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} fullWidth placeholder="e.g. HVAC Technician" />
            <TextField label="Skills" value={skills} onChange={(e) => setSkills(e.target.value)} fullWidth placeholder="Comma-separated" />
            <FormControlLabel
              control={<Switch checked={isAvailable} onChange={(e) => setIsAvailable(e.target.checked)} />}
              label="Available for assignment"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={isSubmitting || (!isEditing && (!email || !password || !fullName))}>
            Save
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
