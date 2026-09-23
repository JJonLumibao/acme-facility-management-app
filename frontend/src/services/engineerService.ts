import { apiRequest } from './apiClient';
import type { EngineerProfile, WorkloadResponse } from '../types';

export interface CreateEngineerPayload {
  email: string;
  password: string;
  full_name: string;
  title?: string;
  skills?: string;
  department?: string | null;
  is_available?: boolean;
}

export type UpdateEngineerPayload = Partial<{
  title: string;
  skills: string;
  department: string | null;
  is_available: boolean;
}>;

export const listEngineers = (): Promise<EngineerProfile[]> => apiRequest<EngineerProfile[]>('/engineers');

/** Engineer workload; pass a category to rank engineers for assigning that kind of incident. */
export const getWorkload = (category?: string): Promise<WorkloadResponse> =>
  apiRequest<WorkloadResponse>('/engineers/workload', { query: { category } });

export const getEngineer = (id: number): Promise<EngineerProfile> => apiRequest<EngineerProfile>(`/engineers/${id}`);

export const createEngineer = (payload: CreateEngineerPayload): Promise<EngineerProfile> =>
  apiRequest<EngineerProfile>('/engineers', { method: 'POST', body: payload });

export const updateEngineer = (id: number, payload: UpdateEngineerPayload): Promise<EngineerProfile> =>
  apiRequest<EngineerProfile>(`/engineers/${id}`, { method: 'PUT', body: payload });

export const deleteEngineer = (id: number): Promise<void> =>
  apiRequest<void>(`/engineers/${id}`, { method: 'DELETE' });
