import { apiRequest } from './apiClient';
import type { DashboardSummary } from '../types';

export const getSummary = (): Promise<DashboardSummary> => apiRequest<DashboardSummary>('/dashboard/summary');
