import { apiRequest } from './apiClient';
import type { User } from '../types';

export function getMe(): Promise<User> {
  return apiRequest<User>('/users/me');
}
