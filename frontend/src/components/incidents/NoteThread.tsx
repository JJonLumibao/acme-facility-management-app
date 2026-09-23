import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import Tooltip from '@mui/material/Tooltip';
import DeleteIcon from '@mui/icons-material/Delete';
import CircularProgress from '@mui/material/CircularProgress';
import { createNote, deleteNote, listNotes } from '../../services/incidentService';
import { ApiError } from '../../services/apiClient';
import ErrorAlert from '../common/ErrorAlert';
import type { IncidentNote, User } from '../../types';
import { ROLE_LABELS, formatDateTime, timeAgo } from '../../utils/format';
import '../../styles/incidents.css';

interface NoteThreadProps {
  incidentId: number;
  currentUser: User | null;
  /** Archived incidents, and closed ones for non-admins, are read-only. */
  isReadOnly?: boolean;
  refreshKey?: unknown;
  onNoteAdded?: () => void;
}

/** Conversation thread between reporter and staff: author-attributed notes plus a reply box. */
export default function NoteThread({ incidentId, currentUser, isReadOnly, refreshKey, onNoteAdded }: NoteThreadProps) {
  const [notes, setNotes] = useState<IncidentNote[]>([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadNotes = useCallback(() => {
    listNotes(incidentId)
      .then(setNotes)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Unable to load notes.'))
      .finally(() => setIsLoading(false));
  }, [incidentId]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes, refreshKey]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!message.trim()) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await createNote(incidentId, message.trim());
      setMessage('');
      loadNotes();
      onNoteAdded?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to add note.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (noteId: number) => {
    try {
      await deleteNote(noteId);
      setNotes((prev) => prev.filter((note) => note.id !== noteId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to delete note.');
    }
  };

  return (
    <div>
      <Typography variant="h6" gutterBottom>
        Notes {notes.length > 0 && <Typography component="span" color="text.secondary">({notes.length})</Typography>}
      </Typography>
      <ErrorAlert message={error} />
      {isLoading ? (
        <CircularProgress size={24} />
      ) : (
        <div className="note-list">
          {notes.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No notes yet. Updates from the team will appear here.
            </Typography>
          )}
          {notes.map((note) => {
            const isMine = currentUser?.id === note.author_id;
            return (
              <div className={`note-item${isMine ? ' note-item-mine' : ''}`} key={note.id}>
                <div className="flex-between" style={{ gap: 8 }}>
                  <div className="note-item-meta">
                    <strong>{isMine ? 'You' : (note.author_name ?? 'Unknown')}</strong>
                    {note.author_role && note.author_role !== 'employee' && (
                      <Chip label={ROLE_LABELS[note.author_role]} size="small" sx={{ height: 18, fontSize: '0.65rem' }} />
                    )}
                    <Tooltip title={formatDateTime(note.created_at)}>
                      <span>{timeAgo(note.created_at)}</span>
                    </Tooltip>
                  </div>
                  {currentUser && (currentUser.role === 'facility_admin' || isMine) && (
                    <IconButton size="small" aria-label="Delete note" onClick={() => handleDelete(note.id)}>
                      <DeleteIcon fontSize="inherit" />
                    </IconButton>
                  )}
                </div>
                <Typography variant="body1" className="note-item-message">
                  {note.message}
                </Typography>
              </div>
            );
          })}
        </div>
      )}
      {isReadOnly ? (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Notes are read-only for this incident.
        </Typography>
      ) : (
        <form onSubmit={handleSubmit} className="flex-row" style={{ marginTop: 16, alignItems: 'flex-end' }}>
          <TextField
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Add a note or question..."
            fullWidth
            size="small"
            multiline
            maxRows={4}
            slotProps={{ htmlInput: { 'aria-label': 'New note' } }}
          />
          <Button type="submit" variant="contained" disabled={isSubmitting || !message.trim()}>
            Send
          </Button>
        </form>
      )}
    </div>
  );
}
