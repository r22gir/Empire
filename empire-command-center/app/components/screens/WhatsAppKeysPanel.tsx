'use client';

import { useEffect, useState, type CSSProperties } from 'react';
import { CheckCircle2, Eye, EyeOff, KeyRound, Loader2, ShieldAlert } from 'lucide-react';
import { loadWhatsAppKeys, saveWhatsAppKeys, type WhatsAppKeyStatus } from '../../lib/companySetup';

const KEYS = [
  { name: 'WHATSAPP_ACCESS_TOKEN', label: 'Access token' },
  { name: 'WHATSAPP_PHONE_NUMBER_ID', label: 'Phone number ID' },
  { name: 'WHATSAPP_APP_SECRET', label: 'App secret' },
  { name: 'WHATSAPP_VERIFY_TOKEN', label: 'Verify token' },
] as const;

export default function WhatsAppKeysPanel({ compact = false }: { compact?: boolean }) {
  const [status, setStatus] = useState<WhatsAppKeyStatus | null>(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [show, setShow] = useState<Record<string, boolean>>({});
  const [form, setForm] = useState<Record<string, string>>({
    WHATSAPP_ACCESS_TOKEN: '',
    WHATSAPP_PHONE_NUMBER_ID: '',
    WHATSAPP_APP_SECRET: '',
    WHATSAPP_VERIFY_TOKEN: '',
    owner_numbers: '',
  });

  const refresh = () =>
    loadWhatsAppKeys()
      .then(setStatus)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load WhatsApp status'));

  useEffect(() => {
    refresh();
  }, []);

  const onSave = async () => {
    setSaving(true);
    setError('');
    setSaved(false);
    try {
      const body: Record<string, unknown> = {};
      for (const key of KEYS) {
        if (form[key.name]?.trim()) body[key.name] = form[key.name].trim();
      }
      const numbers = form.owner_numbers
        .split(/[,\n]/)
        .map((n) => n.trim())
        .filter(Boolean);
      if (numbers.length) body.owner_numbers = numbers;
      const next = await saveWhatsAppKeys(body);
      setStatus(next);
      setForm({
        WHATSAPP_ACCESS_TOKEN: '',
        WHATSAPP_PHONE_NUMBER_ID: '',
        WHATSAPP_APP_SECRET: '',
        WHATSAPP_VERIFY_TOKEN: '',
        owner_numbers: '',
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ background: '#fff', border: '1px solid #e8e4de', borderRadius: 12, padding: compact ? 12 : 16, color: '#1a1a1a' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
        <div className="w-9 h-9 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
          <KeyRound size={16} className="text-[#b8960c]" />
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>WhatsApp keys — this edition</div>
          <div style={{ fontSize: 11, color: '#888' }}>Stored server-side. Never shown back. Never logged.</div>
        </div>
      </div>

      {status && (
        <div style={{ display: 'grid', gap: 6, marginBottom: 14 }}>
          {status.fields.map((field) => (
            <div key={field.key} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '6px 8px', background: '#faf9f7', borderRadius: 6 }}>
              <span style={{ color: '#555' }}>{field.key}</span>
              <span style={{ fontWeight: 600, color: field.set ? '#16a34a' : '#b45309' }}>
                {field.set ? `set ${field.masked}` : 'missing'}
              </span>
            </div>
          ))}
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '6px 8px', background: '#faf9f7', borderRadius: 6 }}>
            <span style={{ color: '#555' }}>Owner numbers</span>
            <span style={{ fontWeight: 600 }}>{status.owner_numbers_set ? `${status.owner_numbers_count} on file` : 'none'}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '6px 8px', background: '#faf9f7', borderRadius: 6 }}>
            <span style={{ color: '#555' }}>Webhook verification</span>
            <span style={{ fontWeight: 600, color: status.webhook.verified ? '#16a34a' : '#888' }}>
              {status.webhook.verified ? 'verified' : status.webhook.reason || 'never challenged'}
            </span>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gap: 8 }}>
        {KEYS.map((key) => (
          <label key={key.name} style={{ display: 'grid', gap: 4, fontSize: 12 }}>
            <span style={{ fontWeight: 600, color: '#333' }}>{key.label}</span>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                type={show[key.name] ? 'text' : 'password'}
                autoComplete="off"
                value={form[key.name]}
                onChange={(e) => setForm((prev) => ({ ...prev, [key.name]: e.target.value }))}
                placeholder="Leave blank to keep the stored value"
                style={inputStyle}
              />
              <button
                type="button"
                onClick={() => setShow((prev) => ({ ...prev, [key.name]: !prev[key.name] }))}
                style={iconBtn}
                aria-label={show[key.name] ? 'Hide' : 'Show'}
              >
                {show[key.name] ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </label>
        ))}
        <label style={{ display: 'grid', gap: 4, fontSize: 12 }}>
          <span style={{ fontWeight: 600, color: '#333' }}>Owner numbers (this edition)</span>
          <textarea
            value={form.owner_numbers}
            onChange={(e) => setForm((prev) => ({ ...prev, owner_numbers: e.target.value }))}
            placeholder="One per line or comma-separated"
            rows={2}
            style={{ ...inputStyle, minHeight: 64, padding: 8 }}
          />
        </label>
      </div>

      {error && (
        <div style={{ marginTop: 10, fontSize: 12, color: '#b91c1c', display: 'flex', alignItems: 'center', gap: 6 }}>
          <ShieldAlert size={14} /> {error}
        </div>
      )}

      <button
        type="button"
        onClick={onSave}
        disabled={saving}
        style={{
          marginTop: 14,
          minHeight: 40,
          padding: '0 16px',
          border: 'none',
          borderRadius: 8,
          background: saved ? '#16a34a' : '#b8960c',
          color: '#fff',
          fontWeight: 700,
          cursor: 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        {saving ? <Loader2 size={14} className="animate-spin" /> : saved ? <CheckCircle2 size={14} /> : <KeyRound size={14} />}
        {saving ? 'Saving…' : saved ? 'Stored' : 'Save keys'}
      </button>
    </div>
  );
}

const inputStyle: CSSProperties = {
  flex: 1,
  minHeight: 38,
  border: '1px solid #e5e2dc',
  borderRadius: 8,
  padding: '0 10px',
  fontSize: 13,
  background: '#fff',
};

const iconBtn: CSSProperties = {
  width: 38,
  border: '1px solid #e5e2dc',
  borderRadius: 8,
  background: '#faf9f7',
  cursor: 'pointer',
};
