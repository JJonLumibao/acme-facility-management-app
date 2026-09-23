import { clearToken, getRefreshToken, getToken, setTokens } from './tokenStore';

// Local dev_server.py (FastAPI wrapper) - routes live at the root, e.g. http://localhost:8000/incidents.
const DEV_API_URL = import.meta.env.VITE_DEV_API_URL || 'http://localhost:8000';
// CORS proxy (bin/proxy-server.js) used for LocalStack/cloud - expects /api/{service-name}/... paths.
const PROXY_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';
const RAW_ENDPOINTS = import.meta.env.VITE_API_ENDPOINTS || '{}';

/**
 * Picks the backend base URL: once Terraform has deployed and populated VITE_API_ENDPOINTS,
 * route through the proxy using the deployed service name; otherwise fall back to the local
 * FastAPI dev server (dev_server.py) for fast iteration without LocalStack/Terraform.
 */
function resolveBaseUrl(): string {
  try {
    const endpoints = JSON.parse(RAW_ENDPOINTS) as Record<string, string>;
    const [serviceName] = Object.keys(endpoints);
    if (serviceName) {
      return `${PROXY_BASE_URL}/api/${serviceName}`;
    }
  } catch {
    // Malformed/missing env value - fall through to the dev server default below.
  }
  return DEV_API_URL;
}

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
}

function buildQueryString(query?: RequestOptions['query']): string {
  if (!query) return '';
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== '') {
      params.set(key, String(value));
    }
  }
  const queryString = params.toString();
  return queryString ? `?${queryString}` : '';
}

/** Fired when the session can't be renewed, so the app can return to the login page. */
export const SESSION_EXPIRED_EVENT = 'acme:session-expired';

// Paths that must never trigger a token refresh (they are how you get tokens in the first place).
const AUTH_PATHS = ['/auth/login', '/auth/register', '/auth/refresh'];

async function send(path: string, options: RequestOptions): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
    // CloudFront strips Authorization from GET requests; the backend also accepts this header.
    headers['X-Auth-Token'] = token;
  }
  try {
    return await fetch(`${resolveBaseUrl()}${path}${buildQueryString(options.query)}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError('Unable to reach the server. Check your connection and try again.', 0);
  }
}

/** Parse a JSON body; empty bodies (e.g. 204 No Content) become null. */
async function readPayload(response: Response): Promise<{ error?: string; details?: unknown } | null> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    // e.g. an HTML page returned by a proxy/CDN instead of the API's JSON.
    throw new ApiError('Unexpected response from the server.', response.status);
  }
}

// One refresh at a time: concurrent 401s all wait for the same renewal.
let refreshInFlight: Promise<boolean> | null = null;

/** Exchange the stored refresh token for a new access token. Returns false if the session is over. */
function refreshSession(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return Promise.resolve(false);
  refreshInFlight ??= (async () => {
    try {
      const response = await send('/auth/refresh', { method: 'POST', body: { refresh_token: refreshToken } });
      if (!response.ok) return false;
      const session = (await readPayload(response)) as { token: string; refresh_token: string } | null;
      if (!session?.token) return false;
      setTokens(session.token, session.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

/**
 * Calls the backend API with the stored access token and returns the parsed JSON body.
 * If the access token has expired, it is renewed once with the refresh token and the request retried;
 * if that fails, tokens are cleared and SESSION_EXPIRED_EVENT is dispatched.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await send(path, options);

  if (response.status === 401 && !AUTH_PATHS.includes(path) && getToken()) {
    if (await refreshSession()) {
      response = await send(path, options);
    } else {
      clearToken();
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
  }

  const payload = await readPayload(response);
  if (!response.ok) {
    const message = payload?.error || response.statusText || 'Request failed';
    throw new ApiError(message, response.status, payload?.details);
  }
  return payload as T;
}
