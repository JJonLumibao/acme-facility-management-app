import { useState } from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Typography from '@mui/material/Typography';
import BarList from './BarList';
import { useCatalog } from '../../context/CatalogContext';
import type { DashboardSummary } from '../../types';
import { formatLocation, timeAgo } from '../../utils/format';
import '../../styles/dashboard.css';

type HotspotLevel = 'buildings' | 'floors' | 'seats';

const LEVELS: Array<{ key: HotspotLevel; label: string }> = [
  { key: 'buildings', label: 'Buildings' },
  { key: 'floors', label: 'Floors' },
  { key: 'seats', label: 'Seats' },
];

/** Locations with the most incidents, plus category+location combinations that keep recurring. */
export default function Hotspots({ hotspots }: { hotspots: NonNullable<DashboardSummary['hotspots']> }) {
  const [level, setLevel] = useState<HotspotLevel>('buildings');
  const { categoryLabel } = useCatalog();

  return (
    <div>
      <Tabs value={level} onChange={(_, value: HotspotLevel) => setLevel(value)} sx={{ mb: 2, minHeight: 36 }}>
        {LEVELS.map((item) => (
          <Tab key={item.key} value={item.key} label={item.label} sx={{ minHeight: 36, py: 0 }} />
        ))}
      </Tabs>
      <BarList
        items={hotspots[level].map((row) => ({
          key: String(row.id),
          label: row.label,
          secondary: row.parent ?? undefined,
          value: row.total,
          detail: `${row.active} still active`,
        }))}
        emptyText={`No incidents linked to specific ${level} yet.`}
      />

      <Typography variant="subtitle2" sx={{ mt: 3, mb: 1 }}>
        Recurring issues (same problem, same place)
      </Typography>
      {hotspots.recurring.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No repeat issues detected.
        </Typography>
      ) : (
        <ul className="recurring-list">
          {hotspots.recurring.map((row, index) => (
            <li key={index}>
              <span className="recurring-count">{row.count}×</span>
              <span>
                <strong>{categoryLabel(row.category)}</strong>
                <br />
                <Typography variant="caption" color="text.secondary">
                  {formatLocation([row.building_name, row.floor_name, row.seat_label])} · last {timeAgo(row.last_reported_at)}
                </Typography>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
