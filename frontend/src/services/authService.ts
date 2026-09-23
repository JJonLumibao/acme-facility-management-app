import { apiRequest } from './apiClient';
import type { AuthResponse, User } from '../types';

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export function register(payload: RegisterPayload): Promise<User> {
  return apiRequest<User>('/auth/register', { method: 'POST', body: payload });
}

export function login(payload: LoginPayload): Promise<AuthResponse> {
  return apiRequest<AuthResponse>('/auth/login', { method: 'POST', body: payload });
}
