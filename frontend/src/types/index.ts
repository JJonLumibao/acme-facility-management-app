export type Role = 'employee' | 'facility_admin' | 'engineer';

export type IncidentStatus = 'open' | 'in_progress' | 'blocked' | 'resolved' | 'closed';

export type IncidentPriority = 'low' | 'medium' | 'high' | 'critical';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  created_at: string;
}

export interface AuthResponse {
  /** Short-lived access token sent with every request. */
  token: string;
  /** Longer-lived token used only to obtain a new access token. */
  refresh_token: string;
  expires_in: number;
  user: User;
}

export interface EngineerProfile {
  user_id: number;
  email: string;
  full_name: string;
  title: string | null;
  skills: string | null;
  department: string | null;
  is_available: boolean;
  created_at: string;
}

export type LoadLevel = 'light' | 'moderate' | 'heavy';

export interface EngineerWorkload extends Omit<EngineerProfile, 'created_at'> {
  active_count: number;
  open_count: number;
  in_progress_count: number;
  blocked_count: number;
  urgent_count: number;
  resolved_30d: number;
  avg_resolve_hours: number | null;
  load_score: number;
  load_level: LoadLevel;
  load_percent: number;
  department_match: boolean;
  recommended: boolean;
}

export interface WorkloadResponse {
  department: string | null;
  thresholds: { moderate: number; heavy: number };
  engineers: EngineerWorkload[];
}

export interface Building {
  id: number;
  name: string;
  address: string | null;
  is_archived: boolean;
  created_at: string;
}

export interface Floor {
  id: number;
  building_id: number;
  name: string;
  is_archived: boolean;
  created_at: string;
}

export interface Seat {
  id: number;
  floor_id: number;
  label: string;
  is_archived: boolean;
  created_at: string;
}

export interface Incident {
  id: number;
  title: string;
  description: string | null;
  category: string;
  status: IncidentStatus;
  priority: IncidentPriority;
  building_id: number | null;
  floor_id: number | null;
  seat_id: number | null;
  building_name: string | null;
  floor_name: string | null;
  seat_label: string | null;
  reported_by: number;
  reporter_name: string | null;
  assigned_to: number | null;
  assignee_name: string | null;
  is_escalated: boolean;
  escalation_reason: string | null;
  blocked_reason: string | null;
  created_at: string;
  updated_at: string;
  acknowledged_at: string | null;
  assigned_at: string | null;
  started_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  last_activity_at: string | null;
  note_count: number;
  /** True when the incident's building/floor/seat was archived; archived incidents are read-only. */
  is_archived: boolean;
  /** Only present on single-incident responses: statuses the current user may move this incident to. */
  allowed_transitions?: IncidentStatus[];
}

export interface IncidentNote {
  id: number;
  incident_id: number;
  author_id: number;
  author_name: string | null;
  author_role: Role | null;
  message: string;
  created_at: string;
}

export type IncidentEventType =
  | 'created'
  | 'status_changed'
  | 'assigned'
  | 'unassigned'
  | 'priority_changed'
  | 'escalated'
  | 'deescalated'
  | 'details_updated'
  | 'note_added';

export interface IncidentEvent {
  id: number;
  incident_id: number;
  actor_id: number | null;
  actor_name: string | null;
  actor_role: Role | null;
  event_type: IncidentEventType;
  from_value: string | null;
  to_value: string | null;
  details: string | null;
  created_at: string;
}

export interface Category {
  key: string;
  label: string;
  group: 'facility' | 'technology' | 'other';
  department: string | null;
  description: string;
}

export interface Department {
  key: string;
  label: string;
}

export interface Catalog {
  categories: Category[];
  departments: Department[];
  statuses: Array<{ key: IncidentStatus; label: string }>;
  transitions: Record<IncidentStatus, IncidentStatus[]>;
  /** True for facility admins in demo/local environments: shows the "Reset demo data" action. */
  demo_reset_enabled?: boolean;
}

export interface MilestoneStat {
  avg_hours: number | null;
  median_hours: number | null;
  count: number;
}

export interface HotspotRow {
  id: number;
  label: string;
  parent: string | null;
  total: number;
  active: number;
}

export interface RecurringIssue {
  category: string;
  building_name: string | null;
  floor_name: string | null;
  seat_label: string | null;
  count: number;
  last_reported_at: string;
}

export interface AttentionItem {
  id: number;
  title: string;
  status: IncidentStatus;
  priority: IncidentPriority;
  category: string;
  is_escalated: boolean;
  escalation_reason: string | null;
  blocked_reason: string | null;
  created_at: string;
  assignee_name: string | null;
  building_name: string | null;
}

export interface CommunicationStats {
  total: number;
  with_staff_update: number;
  staff_update_rate: number | null;
  avg_first_response_hours: number | null;
  finished: number;
  finished_with_update_rate: number | null;
  stale_active: number;
  stale_after_hours: number;
  reopened: number;
}

export interface DashboardSummary {
  kpis: { active: number; unassigned: number; escalated: number; blocked: number; resolved_7d: number; total: number };
  by_status: Partial<Record<IncidentStatus, number>>;
  by_priority: Partial<Record<IncidentPriority, number>>;
  by_category: Array<{ category: string; count: number; active: number }>;
  response_times: Record<'acknowledge' | 'assign' | 'start' | 'resolve', MilestoneStat>;
  needs_attention: AttentionItem[];
  by_assignee: Array<{ assignee_id: number | null; assignee_name: string | null; count: number }> | null;
  hotspots: { buildings: HotspotRow[]; floors: HotspotRow[]; seats: HotspotRow[]; recurring: RecurringIssue[] } | null;
  communication: CommunicationStats | null;
}

export type IncidentSort = 'newest' | 'oldest' | 'updated' | 'priority';

export interface IncidentFilters {
  /** Comma-separated list of statuses. */
  status?: string;
  priority?: IncidentPriority | '';
  category?: string;
  building_id?: number;
  assigned_to?: number;
  escalated?: boolean;
  unassigned?: boolean;
  /** Admins only: list archived incidents instead of live ones. */
  archived?: boolean;
  search?: string;
  sort?: IncidentSort;
}

export const INCIDENT_STATUSES: IncidentStatus[] = ['open', 'in_progress', 'blocked', 'resolved', 'closed'];

export const ACTIVE_STATUSES: IncidentStatus[] = ['open', 'in_progress', 'blocked'];

export const INCIDENT_PRIORITIES: IncidentPriority[] = ['low', 'medium', 'high', 'critical'];

export interface AssistantLink {
  label: string;
  to: string;
}

export interface AssistantReply {
  answer: string;
  links: AssistantLink[];
  suggestions: string[];
}
