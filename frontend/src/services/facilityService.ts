import { apiRequest } from './apiClient';
import type { Building, Floor, Seat } from '../types';

// Archived locations are hidden unless includeArchived is set (only the admin Facilities page needs them).
const archivedQuery = (includeArchived: boolean) => ({ include_archived: includeArchived || undefined });

export const listBuildings = (includeArchived = false): Promise<Building[]> =>
  apiRequest<Building[]>('/buildings', { query: archivedQuery(includeArchived) });

export const createBuilding = (payload: { name: string; address?: string }): Promise<Building> =>
  apiRequest<Building>('/buildings', { method: 'POST', body: payload });

export const updateBuilding = (id: number, payload: Partial<{ name: string; address: string; is_archived: boolean }>): Promise<Building> =>
  apiRequest<Building>(`/buildings/${id}`, { method: 'PUT', body: payload });

export const deleteBuilding = (id: number): Promise<void> =>
  apiRequest<void>(`/buildings/${id}`, { method: 'DELETE' });

export const listFloors = (buildingId: number, includeArchived = false): Promise<Floor[]> =>
  apiRequest<Floor[]>(`/buildings/${buildingId}/floors`, { query: archivedQuery(includeArchived) });

export const createFloor = (buildingId: number, payload: { name: string }): Promise<Floor> =>
  apiRequest<Floor>(`/buildings/${buildingId}/floors`, { method: 'POST', body: payload });

export const updateFloor = (id: number, payload: Partial<{ name: string; is_archived: boolean }>): Promise<Floor> =>
  apiRequest<Floor>(`/floors/${id}`, { method: 'PUT', body: payload });

export const deleteFloor = (id: number): Promise<void> =>
  apiRequest<void>(`/floors/${id}`, { method: 'DELETE' });

export const listSeats = (floorId: number, includeArchived = false): Promise<Seat[]> =>
  apiRequest<Seat[]>(`/floors/${floorId}/seats`, { query: archivedQuery(includeArchived) });

export const createSeat = (floorId: number, payload: { label: string }): Promise<Seat> =>
  apiRequest<Seat>(`/floors/${floorId}/seats`, { method: 'POST', body: payload });

export const updateSeat = (id: number, payload: Partial<{ label: string; is_archived: boolean }>): Promise<Seat> =>
  apiRequest<Seat>(`/seats/${id}`, { method: 'PUT', body: payload });

export const deleteSeat = (id: number): Promise<void> =>
  apiRequest<void>(`/seats/${id}`, { method: 'DELETE' });
