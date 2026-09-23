import { apiRequest } from './apiClient';
import type { Catalog } from '../types';

export const getCatalog = (): Promise<Catalog> => apiRequest<Catalog>('/catalog');
