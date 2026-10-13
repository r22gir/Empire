'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';

function QuoteIntakeForm() {
  const params = useSearchParams();
  const business = params.get('business') || 'empire-workroom';
  const [bizName, setBizName] = useState(business);
  const [form, setForm] = useState({ name: '', email: '', phone: '', city: '', project: '' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ lead_id: number } | null>(null);

  useEffect(() => {
    fetch(`/api/v1/linkinbio/${business}`)
      .then((r) => r.json())
      .then((d) => { if (d?.name) setBizName(d.name); })
      .catch(() => {});
  }, [business]);

  function update(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/leadforge/public/quote-intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_slug: business,
          name: form.name,
          email: form.email,
          phone: form.phone,
          city: form.city,
          project: form.project,
          source_url: `/b/${business}`,
        }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Request failed');
      setDone({ lead_id: body.lead_id });
    } catch (err: any) {
      setError(err.message || 'Request failed');
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div data-testid="quote-thanks" style={{ textAlign: 'center' }}>
        <h1 style={{ fontSize: 26, fontWeight: 900 }}>Request received</h1>
        <p style={{ color: '#525252' }}>
          {bizName} will review your project in LeadForge. Reference #{done.lead_id}.
        </p>
        <Link href={`/b/${business}`} style={{ color: '#0ea5e9' }}>Back to {bizName}</Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} data-testid="quote-intake-form">
      <h1 style={{ fontSize: 26, fontWeight: 900, marginBottom: 6 }}>Request a quote</h1>
      <p style={{ color: '#525252', marginTop: 0 }}>for {bizName}. This creates a LeadForge lead — no spam, no auto-outreach.</p>
      {error && <div style={{ background: '#fef2f2', color: '#b91c1c', padding: 10, borderRadius: 6, marginBottom: 12 }}>{error}</div>}
      {[
        { id: 'name', label: 'Your name', type: 'text', required: true },
        { id: 'email', label: 'Email', type: 'email', required: true },
        { id: 'phone', label: 'Phone (optional)', type: 'tel', required: false },
        { id: 'city', label: 'City (optional)', type: 'text', required: false },
      ].map((field) => (
        <label key={field.id} style={{ display: 'block', marginBottom: 12, fontSize: 13, fontWeight: 700 }}>
          {field.label}
          <input
            type={field.type}
            required={field.required}
            value={(form as any)[field.id]}
            onChange={(e) => update(field.id, e.target.value)}
            style={{ display: 'block', width: '100%', marginTop: 4, padding: 8, fontSize: 14, border: '1px solid #d4d4d4', borderRadius: 6, boxSizing: 'border-box' }}
          />
        </label>
      ))}
      <label style={{ display: 'block', marginBottom: 16, fontSize: 13, fontWeight: 700 }}>
        What do you need?
        <textarea
          required
          value={form.project}
          onChange={(e) => update('project', e.target.value)}
          rows={5}
          style={{ display: 'block', width: '100%', marginTop: 4, padding: 8, fontSize: 14, border: '1px solid #d4d4d4', borderRadius: 6, boxSizing: 'border-box' }}
        />
      </label>
      <button
        type="submit"
        disabled={submitting}
        data-testid="quote-submit"
        style={{ width: '100%', padding: 12, background: '#1a1a1a', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700, fontSize: 15, cursor: 'pointer' }}
      >
        {submitting ? 'Sending…' : 'Send quote request'}
      </button>
    </form>
  );
}

export default function QuoteIntakePage() {
  return (
    <main data-quote-intake-page style={{ maxWidth: 520, margin: '0 auto', padding: '40px 16px 80px', fontFamily: 'system-ui, sans-serif', color: '#1a1a1a' }}>
      <Suspense fallback={<p>Loading…</p>}>
        <QuoteIntakeForm />
      </Suspense>
    </main>
  );
}
