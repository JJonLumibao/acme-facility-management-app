import type { IncidentPriority, IncidentStatus } from '../types';

export const STATUS_LABELS: Record<IncidentStatus, string> = {
  open: 'Open',
  in_progress: 'In Progress',
  blocked: 'Blocked',
  resolved: 'Resolved',
  closed: 'Closed',
};

export const PRIORITY_LABELS: Record<IncidentPriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
};

export const PRIORITY_HINTS: Record<IncidentPriority, string> = {
  low: 'Minor inconvenience, can wait',
  medium: 'Affects my work, but I have a workaround',
  high: 'Blocks my work or affects several people',
  critical: 'Safety risk or affects a whole floor/building',
};

const MS_PER_HOUR = 3_600_000;

/** Human-friendly duration from a number of hours, e.g. 0.4 -> "24m", 5.25 -> "5h 15m", 50 -> "2d 2h". */
export function formatHours(hours: number | null | undefined): string {
  if (hours === null || hours === undefined || Number.isNaN(hours)) return '—';
  const totalMinutes = Math.max(0, Math.round(hours * 60));
  if (totalMinutes < 1) return '<1m';
  const days = Math.floor(totalMinutes / 1440);
  const remHours = Math.floor((totalMinutes % 1440) / 60);
  const minutes = totalMinutes % 60;
  if (days > 0) return remHours ? `${days}d ${remHours}h` : `${days}d`;
  if (remHours > 0) return minutes ? `${remHours}h ${minutes}m` : `${remHours}h`;
  return `${minutes}m`;
}

/** Hours elapsed between two timestamps (end defaults to now). */
export function hoursBetween(start: string, end?: string | null): number {
  const endMs = end ? new Date(end).getTime() : Date.now();
  return (endMs - new Date(start).getTime()) / MS_PER_HOUR;
}

/** Relative time like "5m ago" / "3d ago", falling back to a date for older timestamps. */
export function timeAgo(timestamp: string | null | undefined): string {
  if (!timestamp) return '—';
  const hours = hoursBetween(timestamp);
  if (hours < 1 / 60) return 'just now';
  if (hours < 24 * 14) return `${formatHours(hours)} ago`;
  return new Date(timestamp).toLocaleDateString();
}

export function formatDateTime(timestamp: string | null | undefined): string {
  return timestamp ? new Date(timestamp).toLocaleString() : '—';
}

/** "HQ Tower · 3rd Floor · A-101" from whichever parts are present. */
export function formatLocation(parts: Array<string | null | undefined>): string {
  return parts.filter(Boolean).join(' · ') || 'No location';
}

export const ROLE_LABELS: Record<string, string> = {
  employee: 'Employee',
  engineer: 'Engineer',
  facility_admin: 'Facility Admin',
};
