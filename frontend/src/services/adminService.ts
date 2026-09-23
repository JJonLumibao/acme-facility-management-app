import { apiRequest } from './apiClient';

export interface ResetDemoResult {
  reset: boolean;
  users: number;
  incidents: number;
}

/** Delete all data and restore the demo data set (facility admins, demo environments only). */
export const resetDemoData = (): Promise<ResetDemoResult> =>
  apiRequest<ResetDemoResult>('/admin/reset-demo-data', { method: 'POST', body: { confirm: 'RESET' } });
