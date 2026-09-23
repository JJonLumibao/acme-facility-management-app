import { apiRequest } from './apiClient';
import type { AssistantReply } from '../types';

/** Starter questions for the signed-in user's role. */
export const getAssistantSuggestions = (): Promise<{ suggestions: string[] }> =>
  apiRequest<{ suggestions: string[] }>('/assistant');

/** Ask a question about incidents, locations, response times or workload. */
export const askAssistant = (message: string): Promise<AssistantReply> =>
  apiRequest<AssistantReply>('/assistant', { method: 'POST', body: { message } });
