import { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import AddIcon from '@mui/icons-material/Add';
import type { ReactNode } from 'react';
import { useAuth } from '../context/AuthContext';
import { useCatalog } from '../context/CatalogContext';
import { getSummary } from '../services/dashboardService';
import { getWorkload } from '../services/engineerService';
import { ApiError } from '../services/apiClient';
import ErrorAlert from '../components/common/ErrorAlert';
import StatTile from '../components/dashboard/StatTile';
import BarList from '../components/dashboard/BarList';
import ResponseTimes from '../components/dashboard/ResponseTimes';
import AttentionList from '../components/dashboard/AttentionList';
import Hotspots from '../components/dashboard/Hotspots';
import Communication from '../components/dashboard/Communication';
import WorkDistribution from '../components/dashboard/WorkDistribution';
import CategoryIcon from '../components/incidents/CategoryIcon';
import { STATUS_COLORS, PRIORITY_COLORS } from '../styles/theme';
import { INCIDENT_PRIORITIES, INCIDENT_STATUSES } from '../types';
import type { DashboardSummary, WorkloadResponse } from '../types';
import { PRIORITY_LABELS, STATUS_LABELS } from '../utils/format';
import '../styles/dashboard.css';

function Panel({ title, subtitle, children, wide }: { title: string; subtitle?: string; children: ReactNode; wide?: boolean }) {
  return (
    <Paper className={`dashboard-panel${wide ? ' dashboard-panel-wide' : ''}`} sx={{ p: { xs: 2, sm: 3 } }}>
      <Typography variant="h6" component="h2">
        {title}
      </Typography>
      {subtitle && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {subtitle}
        </Typography>
      )}
      {!subtitle && <Box sx={{ mb: 2 }} />}
      {children}
    </Paper>
  );
}

const INTRO: Record<string, string> = {
  facility_admin: 'Overview of all incidents across ACME facilities.',
  engineer: 'Your assigned incidents and how quickly they are moving.',
  employee: 'Track the incidents you have reported.',
};

export default function DashboardPage() {
  const { user } = useAuth();
  const { categoryLabel } = useCatalog();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [workload, setWorkload] = useState<WorkloadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const isAdmin = user?.role === 'facility_admin';

  useEffect(() => {
    getSummary()
      .then(setSummary)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Unable to load dashboard.'))
      .finally(() => setIsLoading(false));
    if (isAdmin) {
      getWorkload()
        .then(setWorkload)
        .catch(() => setWorkload(null));
    }
  }, [isAdmin]);

  const kpis = summary?.kpis;

  return (
    <Box className="page-container">
      <Box className="flex-between" sx={{ flexWrap: 'wrap', gap: 2, mb: 3 }}>
        <div>
          <Typography variant="h4" component="h1">
            Welcome{user ? `, ${user.full_name.split(' ')[0]}` : ''}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {user ? INTRO[user.role] : ''}
          </Typography>
        </div>
        {user?.role !== 'engineer' && (
          <Button variant="contained" startIcon={<AddIcon />} component={RouterLink} to="/incidents?report=1">
            Report incident
          </Button>
        )}
      </Box>

      <ErrorAlert message={error} />

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        summary &&
        kpis && (
          <>
            <div className="stat-grid">
              <StatTile label="Active incidents" value={kpis.active} to="/incidents?view=active" caption={`${kpis.total} total`} />
              {isAdmin && (
                <StatTile label="Unassigned" value={kpis.unassigned} to="/incidents?view=unassigned" tone={kpis.unassigned ? 'warning' : 'default'} />
              )}
              {user?.role === 'engineer' && (
                <StatTile label="Not started" value={summary.by_status.open ?? 0} to="/incidents?view=todo" />
              )}
              {user?.role === 'employee' && (
                <StatTile
                  label="Awaiting your confirmation"
                  value={summary.by_status.resolved ?? 0}
                  to="/incidents?view=resolved"
                  tone={summary.by_status.resolved ? 'good' : 'default'}
                />
              )}
              <StatTile label="Escalated" value={kpis.escalated} to="/incidents?view=escalated" tone={kpis.escalated ? 'critical' : 'default'} />
              <StatTile label="Blocked" value={kpis.blocked} to="/incidents?view=blocked" tone={kpis.blocked ? 'warning' : 'default'} />
              <StatTile label="Resolved (7 days)" value={kpis.resolved_7d} to="/incidents?view=resolved" />
            </div>

            <div className="dashboard-grid">
              <Panel title="How quickly incidents move" subtitle="Median time from report to each milestone" wide>
                <ResponseTimes times={summary.response_times} />
              </Panel>

              <Panel title="Needs attention" subtitle="Escalated or blocked, and why">
                <AttentionList items={summary.needs_attention} />
              </Panel>

              <Panel title="Incidents by status">
                <BarList
                  items={INCIDENT_STATUSES.map((status) => ({
                    key: status,
                    label: STATUS_LABELS[status],
                    value: summary.by_status[status] ?? 0,
                    color: STATUS_COLORS[status],
                  }))}
                />
              </Panel>

              <Panel title="Most common issues" subtitle="All incidents by category">
                <BarList
                  items={summary.by_category.slice(0, 8).map((row) => ({
                    key: row.category,
                    label: (
                      <span className="flex-row" style={{ gap: 6 }}>
                        <CategoryIcon category={row.category} sx={{ fontSize: 16 }} color="action" />
                        {categoryLabel(row.category)}
                      </span>
                    ),
                    value: row.count,
                    detail: `${row.active} still active`,
                  }))}
                />
              </Panel>

              <Panel title="Incidents by priority">
                <BarList
                  items={INCIDENT_PRIORITIES.map((priority) => ({
                    key: priority,
                    label: PRIORITY_LABELS[priority],
                    value: summary.by_priority[priority] ?? 0,
                    color: PRIORITY_COLORS[priority],
                  }))}
                />
              </Panel>

              {isAdmin && workload && (
                <Panel title="Engineer workload" subtitle="Active tickets per engineer (urgent tickets weigh double)">
                  <WorkDistribution workload={workload} unassigned={kpis.unassigned} />
                </Panel>
              )}

              {summary.hotspots && (
                <Panel title="Hotspots" subtitle="Where issues are reported most">
                  <Hotspots hotspots={summary.hotspots} />
                </Panel>
              )}

              {summary.communication && (
                <Panel title="Keeping employees informed" subtitle="Hover a metric for details" wide>
                  <Communication stats={summary.communication} />
                </Panel>
              )}
            </div>
          </>
        )
      )}
    </Box>
  );
}
