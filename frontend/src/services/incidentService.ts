import { apiRequest } from './apiClient';
import type { Incident, IncidentEvent, IncidentFilters, IncidentNote, IncidentStatus } from '../types';

export interface CreateIncidentPayload {
  title: string;
  category: string;
  building_id: number;
  description?: string;
  priority?: string;
  floor_id?: number;
  seat_id?: number;
}

export interface UpdateIncidentPayload {
  title?: string;
  description?: string;
  category?: string;
  priority?: string;
  status?: IncidentStatus;
  /** Required when blocking, resolving or reopening; also posted to the notes thread. */
  status_reason?: string;
  assigned_to?: number | null;
  is_escalated?: boolean;
  escalation_reason?: string | null;
}

export const listIncidents = (filters: IncidentFilters = {}): Promise<Incident[]> =>
  apiRequest<Incident[]>('/incidents', { query: { ...filters } });

export const getIncident = (id: number): Promise<Incident> => apiRequest<Incident>(`/incidents/${id}`);

export const getIncidentTimeline = (id: number): Promise<IncidentEvent[]> =>
  apiRequest<IncidentEvent[]>(`/incidents/${id}/timeline`);

export const createIncident = (payload: CreateIncidentPayload): Promise<Incident> =>
  apiRequest<Incident>('/incidents', { method: 'POST', body: payload });

export const updateIncident = (id: number, payload: UpdateIncidentPayload): Promise<Incident> =>
  apiRequest<Incident>(`/incidents/${id}`, { method: 'PUT', body: payload });

export const deleteIncident = (id: number): Promise<void> =>
  apiRequest<void>(`/incidents/${id}`, { method: 'DELETE' });

export const listNotes = (incidentId: number): Promise<IncidentNote[]> =>
  apiRequest<IncidentNote[]>(`/incidents/${incidentId}/notes`);

export const createNote = (incidentId: number, message: string): Promise<IncidentNote> =>
  apiRequest<IncidentNote>(`/incidents/${incidentId}/notes`, { method: 'POST', body: { message } });

export const deleteNote = (id: number): Promise<void> =>
  apiRequest<void>(`/notes/${id}`, { method: 'DELETE' });
