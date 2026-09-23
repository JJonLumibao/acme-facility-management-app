import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import InputAdornment from '@mui/material/InputAdornment';
import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';
import PriorityHighIcon from '@mui/icons-material/PriorityHigh';
import BlockIcon from '@mui/icons-material/Block';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutlineOutlined';
import { listIncidents } from '../services/incidentService';
import { listBuildings } from '../services/facilityService';
import { ApiError } from '../services/apiClient';
import { useAuth } from '../context/AuthContext';
import { useCatalog } from '../context/CatalogContext';
import ErrorAlert from '../components/common/ErrorAlert';
import StatusChip from '../components/common/StatusChip';
import PriorityChip from '../components/common/PriorityChip';
import CategoryIcon from '../components/incidents/CategoryIcon';
import IncidentFormDialog from '../components/incidents/IncidentFormDialog';
import { INCIDENT_PRIORITIES } from '../types';
import type { Building, Incident, IncidentFilters, IncidentSort, Role } from '../types';
import { PRIORITY_LABELS, formatHours, formatLocation, hoursBetween, timeAgo } from '../utils/format';
import '../styles/incidents.css';

interface IncidentView {
  key: string;
  label: string;
  filters: IncidentFilters;
  roles?: Role[];
}

/** Quick, role-aware preset filters. Selected via ?view= so dashboard tiles can deep-link to them. */
const VIEWS: IncidentView[] = [
  { key: 'active', label: 'Active', filters: { status: 'open,in_progress,blocked' } },
  { key: 'unassigned', label: 'Unassigned', filters: { status: 'open,in_progress,blocked', unassigned: true }, roles: ['facility_admin'] },
  { key: 'todo', label: 'Not started', filters: { status: 'open' }, roles: ['engineer'] },
  { key: 'escalated', label: 'Escalated', filters: { status: 'open,in_progress,blocked', escalated: true } },
  { key: 'blocked', label: 'Blocked', filters: { status: 'blocked' } },
  { key: 'resolved', label: 'Awaiting confirmation', filters: { status: 'resolved' }, roles: ['employee'] },
  { key: 'resolved', label: 'Resolved', filters: { status: 'resolved' }, roles: ['facility_admin', 'engineer'] },
  { key: 'closed', label: 'Closed', filters: { status: 'closed' } },
  { key: 'archived', label: 'Archived', filters: { archived: true }, roles: ['facility_admin'] },
  { key: 'all', label: 'All', filters: {} },
];

const SORT_LABELS: Record<IncidentSort, string> = {
  newest: 'Newest first',
  oldest: 'Oldest first',
  priority: 'Most urgent',
  updated: 'Recently updated',
};

function ageLabel(incident: Incident): string {
  if (incident.closed_at || incident.resolved_at) {
    return `Resolved in ${formatHours(hoursBetween(incident.created_at, incident.resolved_at ?? incident.closed_at))}`;
  }
  return `Open for ${formatHours(hoursBetween(incident.created_at))}`;
}

export default function IncidentsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { catalog, categoryLabel } = useCatalog();
  const [searchParams, setSearchParams] = useSearchParams();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [search, setSearch] = useState('');
  const [priority, setPriority] = useState('');
  const [category, setCategory] = useState('');
  const [buildingId, setBuildingId] = useState('');
  const [sort, setSort] = useState<IncidentSort>('newest');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isFormOpen, setIsFormOpen] = useState(searchParams.get('report') === '1');

  const isAdmin = user?.role === 'facility_admin';
  const views = useMemo(() => VIEWS.filter((view) => !view.roles || (user && view.roles.includes(user.role))), [user]);
  const viewKey = searchParams.get('view') ?? 'active';
  const activeView = views.find((view) => view.key === viewKey) ?? views[0];
  // Set by the engineer workload tracker ("View N active tickets"); admin-only filter.
  const assigneeParam = isAdmin ? searchParams.get('assignee') : null;

  useEffect(() => {
    listBuildings().then(setBuildings).catch(() => setBuildings([]));
  }, []);

  const loadIncidents = useCallback(() => {
    setIsLoading(true);
    setError(null);
    listIncidents({
      ...activeView.filters,
      search: search.trim() || undefined,
      priority: (priority || undefined) as IncidentFilters['priority'],
      category: category || undefined,
      building_id: buildingId ? Number(buildingId) : undefined,
      assigned_to: assigneeParam ? Number(assigneeParam) : undefined,
      sort,
    })
      .then(setIncidents)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Unable to load incidents.'))
      .finally(() => setIsLoading(false));
  }, [activeView, search, priority, category, buildingId, assigneeParam, sort]);

  useEffect(() => {
    const timeout = setTimeout(loadIncidents, 250);
    return () => clearTimeout(timeout);
  }, [loadIncidents]);

  const selectView = (key: string) => {
    const next = new URLSearchParams(searchParams);
    next.set('view', key);
    next.delete('report');
    setSearchParams(next, { replace: true });
  };

  const hasExtraFilters = Boolean(search || priority || category || buildingId || assigneeParam);

  return (
    <Box className="page-container">
      <Box className="flex-between" sx={{ mb: 2, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4">Incidents</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setIsFormOpen(true)}>
          Report incident
        </Button>
      </Box>

      <Box className="incident-views" role="tablist" aria-label="Incident views">
        {views.map((view) => (
          <Chip
            key={`${view.key}-${view.label}`}
            label={view.label}
            role="tab"
            aria-selected={view.key === activeView.key}
            color={view.key === activeView.key ? 'primary' : 'default'}
            variant={view.key === activeView.key ? 'filled' : 'outlined'}
            onClick={() => selectView(view.key)}
          />
        ))}
      </Box>

      <Box className="incident-filters">
        <TextField
          label="Search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          size="small"
          placeholder="Title, description or #id"
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
        />
        <TextField select label="Category" value={category} onChange={(e) => setCategory(e.target.value)} size="small">
          <MenuItem value="">All categories</MenuItem>
          {catalog?.categories.map((c) => (
            <MenuItem key={c.key} value={c.key}>
              {c.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField select label="Priority" value={priority} onChange={(e) => setPriority(e.target.value)} size="small">
          <MenuItem value="">All priorities</MenuItem>
          {INCIDENT_PRIORITIES.map((p) => (
            <MenuItem key={p} value={p}>
              {PRIORITY_LABELS[p]}
            </MenuItem>
          ))}
        </TextField>
        {buildings.length > 1 && (
          <TextField select label="Building" value={buildingId} onChange={(e) => setBuildingId(e.target.value)} size="small">
            <MenuItem value="">All buildings</MenuItem>
            {buildings.map((b) => (
              <MenuItem key={b.id} value={String(b.id)}>
                {b.name}
              </MenuItem>
            ))}
          </TextField>
        )}
        <TextField select label="Sort" value={sort} onChange={(e) => setSort(e.target.value as IncidentSort)} size="small">
          {(Object.keys(SORT_LABELS) as IncidentSort[]).map((key) => (
            <MenuItem key={key} value={key}>
              {SORT_LABELS[key]}
            </MenuItem>
          ))}
        </TextField>
        {assigneeParam && (
          <Chip
            label={`Assigned to ${incidents[0]?.assignee_name ?? `engineer #${assigneeParam}`}`}
            onDelete={() => {
              const next = new URLSearchParams(searchParams);
              next.delete('assignee');
              setSearchParams(next, { replace: true });
            }}
          />
        )}
        {hasExtraFilters && (
          <Button
            size="small"
            onClick={() => {
              setSearch('');
              setPriority('');
              setCategory('');
              setBuildingId('');
              if (assigneeParam) {
                const next = new URLSearchParams(searchParams);
                next.delete('assignee');
                setSearchParams(next, { replace: true });
              }
            }}
          >
            Clear filters
          </Button>
        )}
      </Box>

      <ErrorAlert message={error} />

      {isLoading && incidents.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : incidents.length === 0 ? (
        <Box className="empty-state">
          <Typography variant="body1" color="text.secondary">
            {hasExtraFilters ? 'No incidents match your filters.' : `No ${activeView.label.toLowerCase()} incidents.`}
          </Typography>
        </Box>
      ) : (
        <Box className="flex-col" sx={{ opacity: isLoading ? 0.6 : 1, transition: 'opacity 150ms' }}>
          <Typography variant="body2" color="text.secondary">
            {incidents.length} incident{incidents.length === 1 ? '' : 's'}
          </Typography>
          {incidents.map((incident) => (
            <Card key={incident.id} className="incident-card" variant="outlined">
              <CardActionArea onClick={() => navigate(`/incidents/${incident.id}`)}>
                <CardContent>
                  <Box className="flex-between" sx={{ flexWrap: 'wrap', gap: 1, alignItems: 'flex-start' }}>
                    <Box className="flex-row" sx={{ gap: 1, minWidth: 0 }}>
                      <CategoryIcon category={incident.category} color="action" />
                      <Typography variant="h6" component="h2" className="incident-card-title">
                        <span className="incident-id">#{incident.id}</span> {incident.title}
                      </Typography>
                    </Box>
                    <Box className="flex-row" sx={{ gap: 1, flexWrap: 'wrap' }}>
                      {incident.is_archived && <Chip label="Archived" size="small" variant="outlined" />}
                      {incident.is_escalated && (
                        <Chip icon={<PriorityHighIcon />} label="Escalated" size="small" color="error" variant="outlined" />
                      )}
                      <StatusChip status={incident.status} />
                      <PriorityChip priority={incident.priority} />
                    </Box>
                  </Box>
                  <Typography variant="body2" color="text.secondary" className="incident-card-meta">
                    <span>{categoryLabel(incident.category)}</span>
                    <span>{formatLocation([incident.building_name, incident.floor_name, incident.seat_label])}</span>
                    {user?.role !== 'employee' && incident.reporter_name && <span>Reported by {incident.reporter_name}</span>}
                    {user?.role !== 'engineer' && (
                      <span>{incident.assignee_name ? `Assigned to ${incident.assignee_name}` : 'Unassigned'}</span>
                    )}
                  </Typography>
                  {incident.status === 'blocked' && incident.blocked_reason && (
                    <Typography variant="body2" className="incident-card-reason">
                      <BlockIcon fontSize="inherit" /> {incident.blocked_reason}
                    </Typography>
                  )}
                  <Typography variant="caption" color="text.secondary" className="incident-card-meta">
                    <span>{ageLabel(incident)}</span>
                    <span>Updated {timeAgo(incident.last_activity_at ?? incident.updated_at)}</span>
                    {incident.note_count > 0 && (
                      <span className="flex-row" style={{ gap: 4 }}>
                        <ChatBubbleOutlineIcon sx={{ fontSize: 14 }} /> {incident.note_count}
                      </span>
                    )}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Box>
      )}

      <IncidentFormDialog
        open={isFormOpen}
        onClose={() => setIsFormOpen(false)}
        onCreated={(incident) => (isAdmin ? loadIncidents() : navigate(`/incidents/${incident.id}`))}
      />
    </Box>
  );
}
