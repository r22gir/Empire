import { API } from './api';

export type ViewerStatus = {
  published: boolean;
  status: string;
  slug?: string | null;
  url?: string | null;
  published_at?: string | null;
  title?: string | null;
  job_id?: string;
  quote_id?: string;
};

export type ViewerPreview = {
  draft: boolean;
  published: boolean;
  auto_published: boolean;
  title: string;
  html: string;
  viewer: ViewerStatus;
  job_id?: string;
  quote_id?: string;
  part_count?: number;
};

export type ViewerPublishResult = {
  published: boolean;
  slug?: string;
  url?: string | null;
  title?: string;
  viewer: ViewerStatus;
};

function viewerBase(jobId?: string | number | null, quoteId?: string | null): string {
  if (jobId) return `/jobs/${encodeURIComponent(String(jobId))}/viewer`;
  if (quoteId) return `/quotes/${encodeURIComponent(String(quoteId))}/viewer`;
  throw new Error('jobId or quoteId is required');
}

async function readJson<T>(res: Response): Promise<T> {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (body as { detail?: string }).detail || `HTTP ${res.status}`;
    const err = new Error(detail) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return body as T;
}

export async function fetchViewerStatus(jobId?: string | number | null, quoteId?: string | null): Promise<ViewerStatus> {
  const res = await fetch(`${API}${viewerBase(jobId, quoteId)}`, { cache: 'no-store' });
  return readJson<ViewerStatus>(res);
}

export async function previewViewer(jobId?: string | number | null, quoteId?: string | null): Promise<ViewerPreview> {
  const res = await fetch(`${API}${viewerBase(jobId, quoteId)}/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  });
  return readJson<ViewerPreview>(res);
}

export async function publishViewer(
  pin: string,
  jobId?: string | number | null,
  quoteId?: string | null,
): Promise<ViewerPublishResult> {
  const res = await fetch(`${API}${viewerBase(jobId, quoteId)}/publish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ founder_pin: pin }),
    cache: 'no-store',
  });
  return readJson<ViewerPublishResult>(res);
}

export async function unpublishViewer(
  pin: string,
  jobId?: string | number | null,
  quoteId?: string | null,
): Promise<ViewerPublishResult> {
  const res = await fetch(`${API}${viewerBase(jobId, quoteId)}/unpublish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ founder_pin: pin }),
    cache: 'no-store',
  });
  return readJson<ViewerPublishResult>(res);
}

export async function copyViewerLink(url: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(url);
    return true;
  } catch {
    const ta = document.createElement('textarea');
    ta.value = url;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand('copy'); } catch { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }
}
