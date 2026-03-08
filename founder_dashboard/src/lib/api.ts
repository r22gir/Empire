import { Task, TaskListResponse, TaskDashboard, Contact, ContactListResponse } from './types';

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(API_URL + path, options);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const entries = Object.entries(params).filter(([, v]) => v != null) as [string, string | number][];
  if (!entries.length) return '';
  return '?' + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const taskApi = {
  list: (params: {
    desk?: string; status?: string; priority?: string;
    assigned_to?: string; due_before?: string;
    limit?: number; offset?: number;
  } = {}) =>
    apiFetch<TaskListResponse>('/tasks' + qs(params)),

  get: (id: string) =>
    apiFetch<{ task: Task & { activity: unknown[]; subtasks: Task[] } }>(`/tasks/${id}`),

  create: (data: {
    title: string; desk: string; description?: string;
    status?: string; priority?: string; assigned_to?: string;
    due_date?: string; tags?: string[]; metadata?: Record<string, unknown>;
  }) =>
    apiFetch<{ task: Task }>('/tasks', json(data)),

  update: (id: string, data: Partial<{
    title: string; description: string; status: string;
    priority: string; desk: string; assigned_to: string;
    due_date: string; tags: string[]; metadata: Record<string, unknown>;
  }>) =>
    apiFetch<{ task: Task }>(`/tasks/${id}`, { ...json(data), method: 'PATCH' }),

  delete: (id: string) =>
    apiFetch<{ status: string; task_id: string }>(`/tasks/${id}`, { method: 'DELETE' }),

  dashboard: () =>
    apiFetch<TaskDashboard>('/tasks/dashboard'),
};

export const costApi = {
  overview: (days = 30) => apiFetch<Record<string, unknown>>(`/costs/overview?days=${days}`),
  today: () => apiFetch<Record<string, unknown>>('/costs/today'),
  daily: (days = 30) => apiFetch<Record<string, unknown>>(`/costs/daily?days=${days}`),
  weekly: (weeks = 12) => apiFetch<Record<string, unknown>>(`/costs/weekly?weeks=${weeks}`),
  monthly: (months = 12) => apiFetch<Record<string, unknown>>(`/costs/monthly?months=${months}`),
  byProvider: (days = 30) => apiFetch<Record<string, unknown>>(`/costs/by-provider?days=${days}`),
  byFeature: (days = 30) => apiFetch<Record<string, unknown>>(`/costs/by-feature?days=${days}`),
  byBusiness: (days = 30) => apiFetch<Record<string, unknown>>(`/costs/by-business?days=${days}`),
  transactions: (limit = 50) => apiFetch<Record<string, unknown>>(`/costs/transactions?limit=${limit}`),
  budget: () => apiFetch<Record<string, unknown>>('/costs/budget'),
  rates: () => apiFetch<Record<string, unknown>>('/costs/rates'),
};

export const contactApi = {
  list: (params: {
    type?: string; search?: string;
    limit?: number; offset?: number;
  } = {}) =>
    apiFetch<ContactListResponse>('/contacts' + qs(params)),

  get: (id: string) =>
    apiFetch<{ contact: Contact }>(`/contacts/${id}`),

  create: (data: {
    name: string; type: string;
    phone?: string; email?: string; address?: string;
    notes?: string; metadata?: Record<string, unknown>;
  }) =>
    apiFetch<{ contact: Contact }>('/contacts', json(data)),

  update: (id: string, data: Partial<{
    name: string; type: string; phone: string;
    email: string; address: string; notes: string;
    metadata: Record<string, unknown>;
  }>) =>
    apiFetch<{ contact: Contact }>(`/contacts/${id}`, { ...json(data), method: 'PATCH' }),

  delete: (id: string) =>
    apiFetch<{ status: string; contact_id: string }>(`/contacts/${id}`, { method: 'DELETE' }),
};
