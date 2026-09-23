import { useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import ErrorAlert from '../common/ErrorAlert';
import { resetDemoData } from '../../services/adminService';
import { ApiError } from '../../services/apiClient';

interface ResetDemoDialogProps {
  open: boolean;
  onClose: () => void;
  onReset: () => void;
}

/** Confirmation dialog for restoring the demo data set; stays open with an error if the reset fails. */
export default function ResetDemoDialog({ open, onClose, onReset }: ResetDemoDialogProps) {
  const [isResetting, setIsResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClose = () => {
    if (isResetting) return; // don't dismiss mid-reset
    setError(null);
    onClose();
  };

  const handleReset = async () => {
    setIsResetting(true);
    setError(null);
    try {
      await resetDemoData();
      onReset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to reset the demo data.');
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>Reset demo data?</DialogTitle>
      <DialogContent>
        <ErrorAlert message={error} />
        <DialogContentText>
          This deletes <strong>all current data</strong> (incidents, notes, buildings and any accounts you created) and
          restores the original demo data. Demo accounts and passwords stay the same. You&apos;ll be signed out.
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isResetting}>
          Cancel
        </Button>
        <Button onClick={handleReset} color="error" variant="contained" disabled={isResetting}>
          {isResetting ? <CircularProgress size={20} color="inherit" /> : 'Reset demo data'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
