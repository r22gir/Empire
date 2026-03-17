const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store/api/v1'
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1');
const AMP_API = `${API}/amp`;

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
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...opts?.headers as Record<string, string> };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${AMP_API}${path}`, { ...opts, headers });
  if (res.status === 401) {
    clearAmpToken();
    if (typeof window !== 'undefined') window.location.href = '/amp/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `Error ${res.status}`);
  }
  return res.json();
}

export async function ampSignup(data: { name: string; email: string; password: string }) {
  const res = await ampFetch<{ token: string; user: any }>('/signup', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  setAmpToken(res.token);
  return res;
}

export async function ampLogin(email: string, password: string) {
  const res = await ampFetch<{ token: string; user: any }>('/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setAmpToken(res.token);
  return res;
}

export async function getAmpMe() {
  return ampFetch<any>('/me');
}
