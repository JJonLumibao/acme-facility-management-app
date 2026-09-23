import { Link as RouterLink } from 'react-router-dom';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import CardActionArea from '@mui/material/CardActionArea';
import type { ReactNode } from 'react';

interface StatTileProps {
  label: string;
  value: ReactNode;
  caption?: string;
  /** Optional deep link, e.g. to a filtered incident view. */
  to?: string;
  tone?: 'default' | 'critical' | 'warning' | 'good';
}

/** Headline number with a label; clickable when `to` is given. */
export default function StatTile({ label, value, caption, to, tone = 'default' }: StatTileProps) {
  const content = (
    <div className={`stat-tile stat-tile-${tone}`}>
      <Typography variant="body2" color="text.secondary" className="stat-tile-label">
        {label}
      </Typography>
      <Typography variant="h4" component="p" className="stat-tile-value">
        {value}
      </Typography>
      {caption && (
        <Typography variant="caption" color="text.secondary">
          {caption}
        </Typography>
      )}
    </div>
  );

  return (
    <Paper variant="outlined" sx={{ height: '100%' }}>
      {to ? (
        <CardActionArea component={RouterLink} to={to} sx={{ height: '100%' }}>
          {content}
        </CardActionArea>
      ) : (
        content
      )}
    </Paper>
  );
}
