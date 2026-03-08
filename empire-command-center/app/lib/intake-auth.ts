const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const INTAKE_API = `${API}/intake`;

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('intake_token');
}

export function setToken(token: string) {
  localStorage.setItem('intake_token', token);
}

export function clearToken() {
  localStorage.removeItem('intake_token');
}

export async function intakeFetch<T = any>(path: string, opts?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...opts?.headers as Record<string, string> };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${INTAKE_API}${path}`, { ...opts, headers });
  if (res.status === 401) {
    clearToken();
    if (typeof window !== 'undefined') window.location.href = '/intake/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `Error ${res.status}`);
  }
  return res.json();
}

export async function intakeUpload(path: string, file: File): Promise<any> {
  const token = getToken();
  const form = new FormData();
  form.append('file', file);
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${INTAKE_API}${path}`, { method: 'POST', headers, body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function signup(data: { name: string; email: string; password: string; phone?: string; company?: string; role?: string }) {
  const res = await intakeFetch<{ token: string; user: any }>('/signup', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  setToken(res.token);
  return res;
}

export async function login(email: string, password: string) {
  const res = await intakeFetch<{ token: string; user: any }>('/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setToken(res.token);
  return res;
}

export async function getMe() {
  return intakeFetch<any>('/me');
}
