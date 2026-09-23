import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';
import '../../styles/dashboard.css';

export interface BarItem {
  key: string;
  label: ReactNode;
  value: number;
  /** Mark color; defaults to the single primary hue (magnitude, not identity). */
  color?: string;
  /** Extra line under the label, e.g. parent building of a floor. */
  secondary?: string;
  /** Extra text for the hover tooltip. */
  detail?: string;
}

/** Horizontal bar list scaled to the largest value, with a hover tooltip carrying exact figures. */
export default function BarList({ items, emptyText = 'No data yet.' }: { items: BarItem[]; emptyText?: string }) {
  const max = Math.max(0, ...items.map((item) => item.value));
  const total = items.reduce((sum, item) => sum + item.value, 0);

  if (items.length === 0 || total === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyText}
      </Typography>
    );
  }

  return (
    <ul className="bar-list">
      {items.map((item) => (
        <Tooltip
          key={item.key}
          placement="top"
          title={`${item.value} (${Math.round((item.value / total) * 100)}% of total)${item.detail ? ` · ${item.detail}` : ''}`}
        >
          <li className="bar-row" tabIndex={0}>
            <span className="bar-label">
              <span className="bar-label-main">{item.label}</span>
              {item.secondary && <span className="bar-label-secondary">{item.secondary}</span>}
            </span>
            <span className="bar-track">
              <span
                className="bar-fill"
                style={{
                  width: `${max ? Math.max((item.value / max) * 100, item.value ? 2 : 0) : 0}%`,
                  backgroundColor: item.color ?? 'var(--chart-primary)',
                }}
              />
            </span>
            <span className="bar-value">{item.value}</span>
          </li>
        </Tooltip>
      ))}
    </ul>
  );
}
