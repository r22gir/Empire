/** Same-origin Studio auth. Cookies stay on the Command Center host. */

function authBase(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  }
  return `${window.location.origin}/api/v1`;
}

async function authFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${authBase()}/auth${path}`, {
    ...opts,
    credentials: 'include',
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(opts?.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = `Auth ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : detail;
    } catch {
      /* ignore */
    }
    const err = new Error(detail) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export type StudioUser = {
  id: string;
  name?: string;
  email?: string;
  role?: string;
  tier?: string;
};

export type StudioSession = {
  authenticated?: boolean;
  user: StudioUser;
  via?: string;
  remember_offered?: boolean;
};

export type TrustedDevice = {
  id: string;
  device_name: string;
  user_agent?: string | null;
  last_used_at?: string | null;
  created_at?: string | null;
  expires_at?: string | null;
  location?: string | null;
  current?: boolean;
};

export async function studioLogin(payload: {
  pin?: string;
  email?: string;
  password?: string;
}): Promise<StudioSession> {
  return authFetch('/studio-login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getStudioSession(): Promise<StudioSession | null> {
  try {
    return await authFetch('/session');
  } catch (err) {
    if ((err as { status?: number }).status === 401) return null;
    throw err;
  }
}

export async function rememberThisDevice(deviceName?: string): Promise<{ ok: boolean; device: TrustedDevice }> {
  return authFetch('/remember-device', {
    method: 'POST',
    body: JSON.stringify(deviceName ? { device_name: deviceName } : {}),
  });
}

export async function listTrustedDevices(): Promise<TrustedDevice[]> {
  const data = await authFetch<{ devices: TrustedDevice[] }>('/devices');
  return data.devices || [];
}

export async function revokeTrustedDevice(id: string): Promise<void> {
  await authFetch(`/devices/${id}`, { method: 'DELETE' });
}

export async function revokeAllTrustedDevices(): Promise<number> {
  const data = await authFetch<{ revoked: number }>('/devices/revoke-all', { method: 'POST' });
  return data.revoked;
}

export async function studioLogout(): Promise<void> {
  try {
    await authFetch('/logout', { method: 'POST' });
  } catch {
    /* still leave the page */
  }
}
