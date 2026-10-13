'use client';

import { useEffect, useState } from 'react';
import { API } from '../../../lib/api';

interface ClientFollowupPrefsProps {
  customerId: string;
}

export default function ClientFollowupPrefs({ customerId }: ClientFollowupPrefsProps) {
  const [quoteOn, setQuoteOn] = useState(false);
  const [invoiceOn, setInvoiceOn] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('Reminders stay off until you enable them for this client.');

  useEffect(() => {
    if (!customerId) return;
    fetch(`${API}/workroom/quotes-commerce/clients/${customerId}/followup-prefs`)
      .then((r) => r.json())
      .then((d) => {
        setQuoteOn(!!d.quote_reminders_enabled);
        setInvoiceOn(!!d.invoice_reminders_enabled);
        setMessage(
          d.quote_reminders_enabled || d.invoice_reminders_enabled
            ? 'Owner opt-in is on for the selected reminder types.'
            : 'Reminders stay off until you enable them for this client.'
        );
      })
      .catch(() => {});
  }, [customerId]);

  const save = async (nextQuote: boolean, nextInvoice: boolean) => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/workroom/quotes-commerce/clients/${customerId}/followup-prefs`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quote_reminders_enabled: nextQuote,
          invoice_reminders_enabled: nextInvoice,
          enabled_by: 'owner',
        }),
      });
      if (!res.ok) throw new Error('save failed');
      setQuoteOn(nextQuote);
      setInvoiceOn(nextInvoice);
      setMessage(
        nextQuote || nextInvoice
          ? 'Owner opt-in saved. Automatic follow-ups will only send for the enabled types.'
          : 'Automatic follow-ups are off for this client.'
      );
    } catch {
      setMessage('Could not save reminder preferences.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #ece8e0', padding: 20 }}>
      <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 8 }}>Quote & invoice follow-ups</h3>
      <p style={{ fontSize: 12, color: '#777', marginBottom: 12 }}>
        Off by default. MAX will not auto-send quote or invoice reminders unless you opt this client in.
      </p>
      <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 8 }}>
        <input type="checkbox" checked={quoteOn} disabled={saving} onChange={(e) => save(e.target.checked, invoiceOn)} />
        Enable quote follow-up reminders
      </label>
      <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 10 }}>
        <input type="checkbox" checked={invoiceOn} disabled={saving} onChange={(e) => save(quoteOn, e.target.checked)} />
        Enable invoice follow-up reminders
      </label>
      <div style={{ fontSize: 11, color: '#166534', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, padding: '8px 10px' }}>
        {message}
      </div>
    </div>
  );
}
