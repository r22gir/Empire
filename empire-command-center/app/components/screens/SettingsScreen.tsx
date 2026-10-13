'use client';

import { useEffect, useState } from 'react';
import { Loader2, MonitorSmartphone, ShieldOff, Trash2 } from 'lucide-react';
import {
  listTrustedDevices,
  revokeAllTrustedDevices,
  revokeTrustedDevice,
  studioLogout,
  type TrustedDevice,
} from '../../lib/studio-auth';

function formatWhen(value?: string | null): string {
  if (!value) return 'Unknown';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  return dt.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export default function SettingsScreen() {
  const [devices, setDevices] = useState<TrustedDevice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const refresh = async () => {
    setError('');
    const items = await listTrustedDevices();
    setDevices(items);
  };

  useEffect(() => {
    refresh()
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load devices'))
      .finally(() => setLoading(false));
  }, []);

  const onRevoke = async (id: string) => {
    if (!window.confirm('Revoke this device? It will have to sign in again immediately.')) return;
    setBusyId(id);
    try {
      await revokeTrustedDevice(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Revoke failed');
    } finally {
      setBusyId(null);
    }
  };

  const onRevokeAll = async () => {
    if (!window.confirm('Revoke every remembered device? You will stay signed in on this session until you leave.')) return;
    setBusyId('all');
    try {
      await revokeAllTrustedDevices();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Revoke all failed');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed', padding: '24px 20px' }}>
      <div style={{ maxWidth: 720, margin: '0 auto' }}>
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
            <MonitorSmartphone size={20} className="text-[#b8960c]" />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Settings</h1>
            <p style={{ fontSize: 12, color: '#888', margin: 0 }}>Trusted devices for Studio sign-in</p>
          </div>
        </div>

        <section data-testid="my-devices" className="rounded-xl overflow-hidden mb-6" style={{ background: 'white', border: '1px solid #e8e4de' }}>
          <div className="px-5 py-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between" style={{ background: '#faf8f4', borderBottom: '1px solid #e8e4de' }}>
            <div>
              <h2 style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>My devices</h2>
              <p style={{ fontSize: 12, color: '#888', margin: '4px 0 0' }}>
                Remembered phones and computers. Revoking invalidates immediately.
              </p>
            </div>
            {devices.length > 0 && (
              <button
                type="button"
                onClick={onRevokeAll}
                disabled={busyId !== null}
                className="flex items-center gap-1.5 text-xs font-semibold"
                style={{ color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer', minHeight: 44 }}
              >
                <ShieldOff size={14} />
                Revoke all
              </button>
            )}
          </div>

          {loading ? (
            <div className="flex justify-center py-10">
              <Loader2 size={22} className="animate-spin text-[#b8960c]" />
            </div>
          ) : error ? (
            <p className="px-5 py-6 text-sm text-[#dc2626]">{error}</p>
          ) : devices.length === 0 ? (
            <p className="px-5 py-8 text-sm text-[#888]">
              No remembered devices yet. After the next sign-in, choose “Remember this device”.
            </p>
          ) : (
            <ul className="divide-y" style={{ borderColor: '#ece8e0' }}>
              {devices.map((device) => (
                <li key={device.id} className="px-5 py-4 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>
                        {device.device_name}
                      </p>
                      {device.current && (
                        <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full" style={{ background: '#fdf8eb', color: '#96750a' }}>
                          This device
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: 12, color: '#777', margin: '4px 0 0' }}>
                      Last used {formatWhen(device.last_used_at)}
                      {device.location ? ` · ${device.location}` : ''}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onRevoke(device.id)}
                    disabled={busyId !== null}
                    className="shrink-0 flex items-center gap-1 text-xs font-semibold"
                    style={{ color: '#dc2626', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, padding: '8px 12px', minHeight: 44, cursor: 'pointer' }}
                  >
                    <Trash2 size={13} />
                    Revoke
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <button
          type="button"
          onClick={async () => {
            await studioLogout();
            window.location.href = '/signin';
          }}
          className="w-full text-sm font-semibold"
          style={{ minHeight: 44, borderRadius: 12, border: '1px solid #e8e4de', background: 'white', color: '#555', cursor: 'pointer' }}
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
