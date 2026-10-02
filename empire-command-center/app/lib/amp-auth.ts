import { API } from './api';

const AMP_API = `${API}/amp`;

/** Old localStorage JWT. The session cookie is the login that counts. */
export function getAmpToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('amp_token');
}

export function setAmpToken(token: string) {
  localStorage.setItem('amp_token', token);
}

export function clearAmpToken() {
  localStorage.removeItem('amp_token');
}

export async function ampFetch<T = any>(path: string, opts?: RequestInit): Promise<T> {
  const token = getAmpToken();
  const headers: Record<string, string> = {
    ...(opts?.body ? { 'Content-Type': 'application/json' } : {}),
    ...(opts?.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${AMP_API}${path}`, { ...opts, headers, credentials: 'include' });
  if (res.status === 401 || res.status === 403) {
    clearAmpToken();
    if (typeof window !== 'undefined') window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `Error ${res.status}`);
  }
  return res.json();
}

export async function getAmpMe() {
  return ampFetch<any>('/me');
}
