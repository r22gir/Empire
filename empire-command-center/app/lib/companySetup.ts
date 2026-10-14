import { API } from './api';

export { GUIDE_LINKS } from './companySetupLinks';

export type CompanySectionId =
  | 'identity'
  | 'contact'
  | 'tax'
  | 'payments'
  | 'numbering'
  | 'services'
  | 'measurements'
  | 'fabric'
  | 'team'
  | 'channels'
  | 'calendar'
  | 'suppliers'
  | 'insurance'
  | 'branding'
  | 'life'
  | 'review';

export interface CompanySection {
  id: CompanySectionId;
  title: string;
  title_es?: string;
  summary: string;
  required?: boolean;
  done?: boolean;
}

export interface CompanyStatus {
  configured: boolean;
  has_name?: boolean;
  has_contact?: boolean;
  missing?: string[];
  completed_sections?: string[];
  interview_complete?: boolean;
  brand_count?: number;
  legal_name?: string;
  default_brand?: string;
}

export interface CompanyInterview {
  edition: string;
  family_edition: boolean;
  founder_edition: boolean;
  progress: {
    current_section: CompanySectionId;
    completed_sections: string[];
    completed: boolean;
    updated_at?: string;
  };
  sections: CompanySection[];
  data: Record<string, any>;
  status: CompanyStatus;
  defaults?: { brands?: any[] };
}

export interface WhatsAppKeyField {
  key: string;
  set: boolean;
  masked: string;
}

export interface WhatsAppKeyStatus {
  edition: string;
  configured: boolean;
  missing: string[];
  fields: WhatsAppKeyField[];
  owner_numbers_count: number;
  owner_numbers_set: boolean;
  webhook: { verified: boolean; reason: string; at: string; endpoint: string };
}

async function companyFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    cache: 'no-store',
    credentials: 'include',
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(opts?.headers || {}) },
  });
  if (res.status === 403) {
    throw new Error('Founder session required');
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    try {
      const parsed = JSON.parse(text);
      const detail = parsed?.detail;
      if (typeof detail === 'string' && detail.trim()) throw new Error(detail);
      if (Array.isArray(detail) && detail[0]?.msg) throw new Error(String(detail[0].msg));
    } catch (err) {
      if (err instanceof Error && err.message && err.message !== text) throw err;
    }
    throw new Error(text || `API ${res.status}`);
  }
  return res.json();
}

export function loadInterview() {
  return companyFetch<CompanyInterview>('/onboarding/interview');
}

export function loadCompanyStatus() {
  return companyFetch<CompanyStatus>('/onboarding/status');
}

/** Public yes/no. Safe without a founder session — does not 403. */
export function loadConfigured() {
  return companyFetch<{ configured: boolean }>('/onboarding/configured');
}

export function saveSection(sectionId: string, data: Record<string, unknown>, markComplete = true) {
  return companyFetch<CompanyInterview>(`/onboarding/interview/${sectionId}`, {
    method: 'PUT',
    body: JSON.stringify({ data, mark_complete: markComplete }),
  });
}

export function saveProgress(currentSection: string) {
  return companyFetch<CompanyInterview>('/onboarding/interview/progress', {
    method: 'POST',
    body: JSON.stringify({ current_section: currentSection }),
  });
}

export function completeInterview() {
  return companyFetch<CompanyInterview>('/onboarding/interview/complete', { method: 'POST' });
}

export function loadReview() {
  return companyFetch<CompanyInterview>('/onboarding/interview/review');
}

export function createInvite(email: string, role: string, name = '') {
  return companyFetch<{ invite: { id: string; email: string; role: string; sent: boolean }; sent: boolean }>(
    '/onboarding/team/invites',
    { method: 'POST', body: JSON.stringify({ email, role, name }) },
  );
}

export function loadWhatsAppKeys() {
  return companyFetch<WhatsAppKeyStatus>('/onboarding/whatsapp');
}

export function saveWhatsAppKeys(body: Record<string, unknown>) {
  return companyFetch<WhatsAppKeyStatus>('/onboarding/whatsapp', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

