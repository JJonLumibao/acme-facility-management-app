import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Tooltip from '@mui/material/Tooltip';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { getWorkload, deleteEngineer } from '../services/engineerService';
import { ApiError } from '../services/apiClient';
import { useCatalog } from '../context/CatalogContext';
import ErrorAlert from '../components/common/ErrorAlert';
import ConfirmDialog from '../components/common/ConfirmDialog';
import EngineerDialog from '../components/engineers/EngineerDialog';
import LoadChip from '../components/engineers/LoadChip';
import type { EngineerProfile, EngineerWorkload, WorkloadResponse } from '../types';
import { formatHours } from '../utils/format';
import '../styles/engineers.css';

type SortKey = 'load' | 'name';

function toProfile(engineer: EngineerWorkload): EngineerProfile {
  return { ...engineer, created_at: '' };
}

/** Engineer management + workload tracker: who is available, how loaded they are, and in which department. */
export default function EngineersPage() {
  const { catalog, departmentLabel } = useCatalog();
  const [workload, setWorkload] = useState<WorkloadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [department, setDepartment] = useState('');
  const [sort, setSort] = useState<SortKey>('load');
  const [dialog, setDialog] = useState<{ open: boolean; engineer: EngineerProfile | null }>({ open: false, engineer: null });
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const loadWorkload = useCallback(() => {
    setIsLoading(true);
    getWorkload()
      .then(setWorkload)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Unable to load engineers.'))
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(loadWorkload, [loadWorkload]);

  const engineers = useMemo(() => {
    const list = (workload?.engineers ?? []).filter(
      (engineer) => !department || (department === 'none' ? !engineer.department : engineer.department === department),
    );
    return list.sort((a, b) =>
      sort === 'load' ? b.load_score - a.load_score || a.full_name.localeCompare(b.full_name) : a.full_name.localeCompare(b.full_name),
    );
  }, [workload, department, sort]);

  const overloaded = engineers.filter((engineer) => engineer.is_available && engineer.load_level === 'heavy');
  const available = engineers.filter((engineer) => engineer.is_available);

  const handleDelete = async () => {
    if (confirmDeleteId === null) return;
    try {
      await deleteEngineer(confirmDeleteId);
      loadWorkload();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? 'This engineer has ticket history and cannot be deleted. Mark them unavailable instead.'
          : err instanceof ApiError
            ? err.message
            : 'Unable to delete engineer.',
      );
    } finally {
      setConfirmDeleteId(null);
    }
  };

  return (
    <Box className="page-container">
      <Box className="flex-between" sx={{ mb: 1, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" component="h1">
          Engineers
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog({ open: true, engineer: null })}>
          Add engineer
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Load counts active tickets, with high/critical tickets weighing double. Moderate from{' '}
        {workload?.thresholds.moderate ?? 3}, heavy from {workload?.thresholds.heavy ?? 6}.
      </Typography>

      <ErrorAlert message={error} />

      <Box className="incident-filters" sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 3 }}>
        <TextField select size="small" label="Department" value={department} onChange={(e) => setDepartment(e.target.value)} sx={{ minWidth: 200 }}>
          <MenuItem value="">All departments</MenuItem>
          {catalog?.departments.map((d) => (
            <MenuItem key={d.key} value={d.key}>
              {d.label}
            </MenuItem>
          ))}
          <MenuItem value="none">No department</MenuItem>
        </TextField>
        <TextField select size="small" label="Sort" value={sort} onChange={(e) => setSort(e.target.value as SortKey)} sx={{ minWidth: 160 }}>
          <MenuItem value="load">Busiest first</MenuItem>
          <MenuItem value="name">Name</MenuItem>
        </TextField>
        {workload && (
          <Typography variant="body2" color="text.secondary" sx={{ alignSelf: 'center' }}>
            {available.length} of {engineers.length} available
          </Typography>
        )}
      </Box>

      {overloaded.length > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {overloaded.map((engineer) => engineer.full_name).join(', ')} {overloaded.length === 1 ? 'has' : 'have'} a heavy
          workload. Consider reassigning some of their tickets to a colleague in the same department.
        </Alert>
      )}

      {isLoading && !workload ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : engineers.length === 0 ? (
        <Typography color="text.secondary">
          {department ? 'No engineers in this department.' : 'No engineer profiles yet.'}
        </Typography>
      ) : (
        <div className="engineer-grid">
          {engineers.map((engineer) => (
            <Card key={engineer.user_id} variant="outlined" className={engineer.is_available ? '' : 'engineer-card-away'}>
              <CardContent>
                <Box className="flex-between" sx={{ alignItems: 'flex-start', gap: 1 }}>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="h6" component="h2" sx={{ lineHeight: 1.3 }}>
                      {engineer.full_name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" noWrap>
                      {engineer.title || 'Engineer'} · {departmentLabel(engineer.department)}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', flex: 'none' }}>
                    <IconButton size="small" aria-label={`Edit ${engineer.full_name}`} onClick={() => setDialog({ open: true, engineer: toProfile(engineer) })}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" aria-label={`Delete ${engineer.full_name}`} onClick={() => setConfirmDeleteId(engineer.user_id)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </Box>

                <Box className="flex-row" sx={{ gap: 1, mt: 1.5, flexWrap: 'wrap' }}>
                  {engineer.is_available ? <LoadChip level={engineer.load_level} /> : <Chip size="small" label="Unavailable" />}
                  {engineer.skills && (
                    <Typography variant="caption" color="text.secondary">
                      {engineer.skills}
                    </Typography>
                  )}
                </Box>

                <Tooltip title={`Load score ${engineer.load_score} (heavy at ${workload?.thresholds.heavy ?? 6})`}>
                  <div className="engineer-load-track" aria-label={`Load ${engineer.load_percent}%`}>
                    <span className={`engineer-load-fill load-${engineer.load_level}`} style={{ width: `${engineer.load_percent}%` }} />
                  </div>
                </Tooltip>

                <dl className="engineer-stats">
                  <div>
                    <dt>Active</dt>
                    <dd>{engineer.active_count}</dd>
                  </div>
                  <div>
                    <dt>In progress</dt>
                    <dd>{engineer.in_progress_count}</dd>
                  </div>
                  <div>
                    <dt>Blocked</dt>
                    <dd>{engineer.blocked_count}</dd>
                  </div>
                  <div>
                    <dt>Urgent</dt>
                    <dd>{engineer.urgent_count}</dd>
                  </div>
                  <div>
                    <dt>Resolved 30d</dt>
                    <dd>{engineer.resolved_30d}</dd>
                  </div>
                  <div>
                    <dt>Avg resolve</dt>
                    <dd>{formatHours(engineer.avg_resolve_hours)}</dd>
                  </div>
                </dl>

                {engineer.active_count > 0 && (
                  <Button size="small" component={RouterLink} to={`/incidents?view=active&assignee=${engineer.user_id}`} sx={{ mt: 1, px: 0 }}>
                    View {engineer.active_count} active ticket{engineer.active_count === 1 ? '' : 's'}
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <EngineerDialog
        open={dialog.open}
        engineer={dialog.engineer}
        onClose={() => setDialog({ open: false, engineer: null })}
        onSaved={loadWorkload}
      />
      <ConfirmDialog
        open={confirmDeleteId !== null}
        title="Delete engineer"
        message="This removes the engineer's account entirely. Engineers with ticket history can't be deleted; mark them unavailable instead."
        onCancel={() => setConfirmDeleteId(null)}
        onConfirm={handleDelete}
      />
    </Box>
  );
}
